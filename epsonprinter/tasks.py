import uuid
import time
import traceback
from time import sleep

import requests
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from channels.layers import get_channel_layer
from django.utils import timezone

from APIcashless.models import CommandeSauvegarde, GroupementCategorie, ArticleVendu, Articles, Configuration
from Cashless.celery import app
import logging
from asgiref.sync import async_to_sync

from .views import print_command as print_command_epson
from .views import article_direct_to_printer, TicketZ_PiEpson_Printer
from .sunmi_cloud_printer import SunmiCloudPrinter, ALIGN_CENTER, ALIGN_LEFT

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=10)
def send_print_order_inner_sunmi(self, ws_channel, data):
    """
    Send a print order to a websocket channel and wait for a response from the printer.
    Will retry up to 10 times with exponential backoff if an error occurs or if no response is received within 10 seconds.

    Args:
        ws_channel (str): The websocket channel to send the order to
        data (dict): The data to send

    Returns:
        bool: True if the order was successfully sent and a response was received, False otherwise
    """

    # Le max de temps entre deux retries : 1 heure
    MAX_RETRY_TIME = 60 * 1 * 1  # 1 minutes pour tester

    # Generate a unique UUID for this print order
    order_uuid = uuid.uuid4()

    logger.info(f"send_print_order : tentative d'envoi de message vers WS sur le canal {ws_channel}")
    try:

        # Send the message to the websocket channel
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            ws_channel,
            {
                'type': 'chat_message',
                'message': f'print_order@{order_uuid}',
                'data': data,
            }
        )
        logger.info(
            f"send_print_order : message envoyé avec succès vers WS sur le canal {ws_channel} avec UUID {order_uuid}")

        # TODO: Checker la réponse et raise une erreur pour retry
        response_received = True
        return True

    except Exception as exc:
        # Ajoute un backoff exponentiel pour les autres erreurs
        retry_delay = min(2 ** self.request.retries, MAX_RETRY_TIME)
        logger.error(
            f"WS : erreur lors de l'envoi du message vers WS sur le canal {ws_channel}: {exc}\n next retry in {retry_delay} seconds...")
        raise self.retry(exc=exc, countdown=retry_delay)
    except MaxRetriesExceededError:
        logger.error(f"send_print_order : La tâche a échoué après plusieurs tentatives pour {order_uuid}")
        return False


@app.task
def print_command(commande_pk, groupement_solo_pk=None):
    """
    Unified function to print a command ticket using the appropriate printer based on the printer type.

    Args:
        commande_pk: The primary key of the CommandeSauvegarde object
        groupement_solo_pk: Optional primary key of a specific GroupementCategorie to print

    Returns:
        bool: True if all print jobs were successfully sent, False otherwise
    """
    try:
        # Get the command from the database
        # C'est une fonction atomic qui le lance on va attendre un peu et tester
        time.sleep(1)
        start_time = time.time()
        commande = None

        while time.time() - start_time < 5:
            try:
                commande = CommandeSauvegarde.objects.get(pk=commande_pk)
                break  # Si la commande est trouvée, on sort de la boucle
            except CommandeSauvegarde.DoesNotExist:
                time.sleep(0.5)  # Attente de 500ms avant la prochaine tentative
                continue

        # Si après 5 secondes la commande n'est toujours pas trouvée
        if not commande:
            logger.error(f"La commande {commande_pk} n'a pas été trouvée après 5 secondes d'attente")
            return False


        # Get the specific groupement if provided
        groupement_solo = None
        if groupement_solo_pk:
            groupement_solo = GroupementCategorie.objects.get(pk=groupement_solo_pk)

        logger.info(f"PRINT: Unified print_command: {commande} - {groupement_solo}")

        # Get all groupements
        groupements = GroupementCategorie.objects.all()

        # Get all article lines from the command
        lignes_articles = commande.articles.all()

        # Group articles by groupement
        articles_groupe = {}
        for groupement in groupements:
            # If a specific groupement is provided, only process that one
            if groupement_solo and groupement != groupement_solo:
                continue

            articles_groupe[groupement] = []
            categories_groupees = groupement.categories.all()
            for ligne_article in lignes_articles:
                if ligne_article.article.categorie in categories_groupees:
                    articles_groupe[groupement].append(ligne_article)

        # Process each group of articles
        success = True
        for groupe, lignes_article in articles_groupe.items():
            if len(lignes_article) > 0 and groupe.printer:
                # Determine the printer type and call the appropriate print function
                printer_type = groupe.printer.printer_type

                if printer_type == groupe.printer.EPSON_PI:
                    logger.info(f"PRINT : epsonprinter.tasks.print_command -> print_command_epsonTM20 : {commande} - {groupe}")
                    # For Epson printers, we need to pass the whole command and optionally the groupement
                    # Pas besoin du groupe, la TM20 reconstruit le dict avec les articles
                    result = print_command_epson_tm20(commande, groupe if groupement_solo else None)
                elif printer_type in [groupe.printer.SUNMI_INTEGRATED_80, groupe.printer.SUNMI_INTEGRATED_57]:
                    logger.info(f"PRINT : epsonprinter.tasks.print_command -> print_command_inner_sunmi : {commande} - {groupe}")
                    # For Sunmi integrated printers
                    result = print_command_inner_sunmi(commande, groupe, lignes_article)
                elif printer_type == groupe.printer.SUNMI_CLOUD:
                    logger.info(f"PRINT : epsonprinter.tasks.print_command -> print_command_sunmi_cloud : {commande} - {groupe}")
                    # For Sunmi Cloud printers
                    result = print_command_sunmi_cloud(commande, groupe, lignes_article)
                else:
                    logger.error(f"Unknown printer type {printer_type} for group {groupe.name}")
                    result = False

                # If any print job fails, set success to False
                if not result:
                    success = False

        return success
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error in unified print_command: {e}")
        return False


@app.task
def print_command_inner_sunmi(commande, groupe, lignes_article):
    """
    Print a command ticket using the Sunmi integrated printer.

    Args:
        commande: The CommandeSauvegarde object
        groupe: The GroupementCategorie object
        lignes_article: List of article lines to print

    Returns:
        bool: True if the print job was successfully sent, False otherwise
    """
    if not groupe.printer or not groupe.printer.host or not groupe.printer.host.user:
        logger.error(f"Printer configuration incomplete for group {groupe.name}")
        return False

    ws_channel = groupe.printer.host.user.uuid.hex
    # fabrication du ticket en envoi à l'imprimante

    # Les imrpimantes 57mm des Sunmi ne prennent pas l'ordre "line"n on fabrique le texte avec ----
    printer_type = groupe.printer.printer_type # SUNMI_INTEGRATED_80 = 'S8' ou SUNMI_INTEGRATED_57 = 'S5'
    line = {"type": "line", "value": "single"} if printer_type == 'S8' else {"type": "text", "value": "-"*32}

    # Header contenant les infos générales
    base_ticket = [
        {"type": "size", "value": 0},
        line,
        {"type": "size", "value": 1},
        {"type": "text", "value": f"{commande.datetime.astimezone().strftime('%d/%m/%Y %H:%M')}"},
        {"type": "bold", "value": 1},
        {"type": "text", "value": f"TABLE : {commande.table.name}"},
        {"type": "bold", "value": 0},
        {"type": "text", "value": f"{commande.responsable.name}"},
        {"type": "text", "value": f"ID : {commande.id_commande()[:3]}"},
        {"type": "size", "value": 0},
        line,
    ]

    # Quel est le numéro ?
    numero = commande.numero_du_ticket_imprime.get(groupe.name)
    if numero:
        title = f"{groupe.name} {numero}"
    else:
        groupe.compteur_ticket_journee += 1
        commande.numero_du_ticket_imprime[groupe.name] = groupe.compteur_ticket_journee
        groupe.save()
        commande.save()
        title = f"{groupe.name} {groupe.compteur_ticket_journee}"

    ticket = [
        {"type": "font", "value": "A"},
        {"type": "size", "value": 1},
        {"type": "bold", "value": 1},
        {"type": "align", "value": "left"},
        {"type": "text", "value": f"{title}"},
        {"type": "align", "value": "left"},
        {"type": "size", "value": 0},
        line,
        {"type": "size", "value": 1}, # taille 1 pour les articles qui suivent
    ]
    for ligne in lignes_article:
        ticket.append({"type": "text", "value": f"{int(ligne.qty)} x {ligne.article.name}"}, )

    ticket += [
        {"type": "size", "value": 0},
        line,
        {"type": "feed", "value": 2},
        {"type": "cut"},
    ]

    send_print_order_inner_sunmi.delay(ws_channel, base_ticket + ticket)
    logger.info(f"Print job sent to Sunmi integrated printer for {title}")

    return True


@app.task
def print_command_epson_tm20(commande, groupement_solo=None):
    """
    Print a command ticket using the Epson TM20 printer.

    Args:
        commande: The CommandeSauvegarde object
        groupement_solo: Optional GroupementCategorie object to print only for this group

    Returns:
        bool: True if the print job was successfully sent, False otherwise
    """
    logger.info(f"print_command_epson_tm20 : {commande} - {groupement_solo}")

    ticket = print_command_epson(commande, groupement_solo)

    if ticket.can_print():
        logger.info(f"   print_command_epson_tm20 ticket.can_print() True -> ticket.to_printer()")
        # TODO: Tester max retry avec le débranchage de l'imprimante
        ticket.to_printer()
        return True

    return False


@app.task
def direct_to_print(article_vendu_pk):
    article_vendu = ArticleVendu.objects.get(pk=article_vendu_pk)
    logger.info(f"DIRECT TO PRINT : {article_vendu}")
    ticket = article_direct_to_printer(article_vendu)

    if ticket.can_print():
        logger.info(f"   ticket.can_print() -> PRINT")
        ticket.to_printer()


@app.task
def ticketZ_tasks_printer(ticketz_json):
    logger.info(f"   ticketZ_printer(ticketz_json) -> PRINT")
    ticket_Z = TicketZ_PiEpson_Printer(ticketz_json)
    if ticket_Z.can_print():
        logger.info(f"   ticket_Z.can_print() -> PRINT")
        ticket_Z.to_printer()
    else:
        print(ticket_Z._header())
        print(ticket_Z._body())
        print(ticket_Z._footer())


@app.task
def print_ticket_purchases_task(ticket_data):
    """
    Print a purchase receipt to all available printers.

    Args:
        ticket_data (dict): A dictionary containing all the information needed for the receipt.
            The dictionary should include:
            - business_name: Name of the business
            - business_address: Address of the business
            - business_siret: SIRET number
            - business_vat_number: VAT number
            - business_phone: Phone number
            - business_email: Email address
            - date_time: Date and time of the purchase
            - receipt_id: Receipt ID
            - table: Table name
            - server: Server name
            - articles: List of articles with name, quantity, unit_price, total_price, vat_rate
            - total_ttc: Total TTC
            - total_ht: Total HT
            - total_tva: Total TVA
            - payment_method: Payment method
            - footer: Footer text

    Returns:
        bool: True if the print job was successfully sent to at least one printer, False otherwise
    """
    from .views import remove_accents

    logger.info(f"Printing purchase receipt: {ticket_data['receipt_id']}")

    # Get all printers
    from .models import Printer
    printer = Printer.objects.get(id=ticket_data['printer_id'])

    try:
        printer_type = printer.printer_type

        # Handle Epson printers
        if printer_type == Printer.EPSON_PI:
            success = print_ticket_purchases_epson(ticket_data, printer)

        # Handle Sunmi integrated printers (57mm)
        elif printer_type == Printer.SUNMI_INTEGRATED_57:
            success = print_ticket_purchases_sunmi_57(ticket_data, printer)

        # Handle Sunmi integrated printers (80mm)
        elif printer_type == Printer.SUNMI_INTEGRATED_80:
            success = print_ticket_purchases_sunmi_80(ticket_data, printer)

        # Handle Sunmi Cloud printers
        elif printer_type == Printer.SUNMI_CLOUD:
            success = print_ticket_purchases_sunmi_cloud(ticket_data, printer, 57)

        else:
            logger.error(f"Unknown printer type: {printer_type}")

    except Exception as e:
        logger.error(f"Error printing to {printer.name}: {e}")
        traceback.print_exc()

    return True

def print_ticket_purchases_epson(ticket_data, printer):
    """
    Print a purchase receipt to an Epson printer.

    Args:
        ticket_data (dict): The ticket data dictionary
        printer (Printer): The printer object

    Returns:
        bool: True if the print job was successfully sent, False otherwise
    """
    from .views import remove_accents

    try:
        # Create header
        header = []
        header.append("-" * 32)
        if ticket_data['business_address']:
            header.append(remove_accents(ticket_data['business_address']))
        if ticket_data['business_siret']:
            header.append(f"SIRET: {ticket_data['business_siret']}")
        if ticket_data['business_vat_number']:
            header.append(f"TVA: {ticket_data['business_vat_number']}")
        header.append("-" * 32)
        header.append(f"DATE: {ticket_data['date_time']}")
        header.append(f"TICKET: {ticket_data['receipt_id']}")
        if ticket_data['table']:
            header.append(f"TABLE: {remove_accents(ticket_data['table'])}")
        if ticket_data['server']:
            header.append(f"SERVEUR: {remove_accents(ticket_data['server'])}")
        header.append("-" * 32)

        # Create body with articles
        body = []
        for article in ticket_data['articles']:
            name = remove_accents(article['name'])
            qty = article['quantity']
            price = article['unit_price']
            total = article['total_price']

            # Format: NAME QTY x PRICE = TOTAL
            body.append(f"{name} {qty} x {price} = {total}")

        body.append("-" * 32)
        body.append(f"TOTAL HT: {ticket_data['total_ht']}")
        body.append(f"TVA: {ticket_data['total_tva']}")
        body.append(f"TOTAL TTC: {ticket_data['total_ttc']}")
        body.append(f"PAIEMENT: {remove_accents(ticket_data['payment_method'])}")

        # Create footer
        footer = []
        footer.append("-" * 32)
        if ticket_data['footer']:
            footer.append(remove_accents(ticket_data['footer']))
        footer.append("\n\n\n")  # Add some space at the end

        # Create a ticket object

        req = requests.session()
        try:
            # Pour serveur sous flask :
            reponse = req.post(f'{printer.serveur_impression}',
                               data={
                                   'coucouapi': printer.api_serveur_impression,
                                   'adresse_printer': printer.thermal_printer_adress,
                                   'copy': '1',
                                   'title': f"{ticket_data['business_name'].upper()}",
                                   'header': "\n".join(header),
                                   'body': "\n".join(body),
                                   'footer': "\n".join(footer),
                               })
            logger.info(f"REPONSE Serveur impression : {reponse.status_code} - {reponse.text}")
        except ConnectionError:
            logger.error(f"print_command ConnectionError for {printer.thermal_printer_adress} ")
        except Exception as e:
            logger.error(f"print_command Exception for {printer.thermal_printer_adress} : {e}")

        req.close()
        return True

    except Exception as e:
        logger.error(f"Error printing to Epson printer {printer.name}: {e}")
        traceback.print_exc()
        return False

def print_ticket_purchases_sunmi_57(ticket_data, printer):
    """
    Print a purchase receipt to a Sunmi integrated 57mm printer.

    Args:
        ticket_data (dict): The ticket data dictionary
        printer (Printer): The printer object

    Returns:
        bool: True if the print job was successfully sent, False otherwise
    """
    from .views import remove_accents

    try:
        if not printer.host or not printer.host.user:
            logger.error(f"Printer configuration incomplete for {printer.name}")
            return False

        ws_channel = printer.host.user.uuid.hex

        # Create the ticket
        ticket = [
            {"type": "size", "value": 0},
            {"type": "bold", "value": 1},
            {"type": "align", "value": "left"},
            {"type": "text", "value": remove_accents(ticket_data['business_name'].upper())},
            {"type": "bold", "value": 0},
        ]

        # Add business information
        if ticket_data['business_address'] and ticket_data['business_address'] != 'None':
            ticket.append({"type": "text", "value": remove_accents(ticket_data['business_address'])})
        if ticket_data['business_siret']:
            ticket.append({"type": "text", "value": f"SIRET: {ticket_data['business_siret']}"})
        if ticket_data['business_vat_number']:
            ticket.append({"type": "text", "value": f"TVA: {ticket_data['business_vat_number']}"})

        ticket.extend([
            {"type": "text", "value": "--------------------------------"},
            {"type": "align", "value": "left"},
            {"type": "text", "value": f"DATE: {ticket_data['date_time']}"},
            {"type": "text", "value": f"TICKET: {ticket_data['receipt_id']}"},
        ])

        if ticket_data['table']:
            ticket.append({"type": "text", "value": f"TABLE: {remove_accents(ticket_data['table'])}"})
        if ticket_data['server']:
            ticket.append({"type": "text", "value": f"SERVEUR: {remove_accents(ticket_data['server'])}"})

        ticket.append({"type": "text", "value": "--------------------------------" })

        # Add articles
        for article in ticket_data['articles']:
            name = remove_accents(article['name'])
            qty = article['quantity']
            price = article['unit_price']
            total = article['total_price']

            ticket.append({"type": "text", "value": name})
            ticket.append({"type": "text", "value": f"{qty} x {price} = {total}"})

        # Add totals
        ticket.extend([
            {"type": "text", "value": "--------------------------------"},
            {"type": "text", "value": f"TOTAL HT: {ticket_data['total_ht']}"},
            {"type": "text", "value": f"TVA: {ticket_data['total_tva']}"},
            {"type": "bold", "value": 1},
            {"type": "text", "value": f"TOTAL TTC: {ticket_data['total_ttc']}"},
            {"type": "bold", "value": 0},
            {"type": "text", "value": f"PAIEMENT: {remove_accents(ticket_data['payment_method'])}"},
        ])

        # Add footer
        ticket.extend([
            {"type": "text", "value": "--------------------------------"},
            {"type": "align", "value": "center"},
        ])

        if ticket_data['footer']:
            ticket.append({"type": "text", "value": remove_accents(ticket_data['footer'])})

        # Add final commands
        ticket.extend([
            {"type": "feed", "value": 3},
            {"type": "cut"},
        ])

        # Send the ticket to the printer
        send_print_order_inner_sunmi.delay(ws_channel, ticket)
        logger.info(f"Receipt printed to Sunmi 57mm printer: {printer.name}")
        return True

    except Exception as e:
        logger.error(f"Error printing to Sunmi 57mm printer {printer.name}: {e}")
        traceback.print_exc()
        return False

def print_ticket_purchases_sunmi_80(ticket_data, printer):
    """
    Print a purchase receipt to a Sunmi integrated 80mm printer.

    Args:
        ticket_data (dict): The ticket data dictionary
        printer (Printer): The printer object

    Returns:
        bool: True if the print job was successfully sent, False otherwise
    """
    from .views import remove_accents

    try:
        if not printer.host or not printer.host.user:
            logger.error(f"Printer configuration incomplete for {printer.name}")
            return False

        ws_channel = printer.host.user.uuid.hex

        # Create the ticket - similar to 57mm but with more space
        ticket = [
            {"type": "size", "value": 0},
            {"type": "bold", "value": 1},
            {"type": "align", "value": "center"},
            {"type": "text", "value": ""},
            {"type": "text", "value": remove_accents(ticket_data['business_name'].upper())},
            {"type": "bold", "value": 0},
        ]

        # Add business information
        if ticket_data['business_address'] and ticket_data['business_address'] != 'None':
            ticket.append({"type": "text", "value": remove_accents(ticket_data['business_address'])})
        if ticket_data['business_siret']:
            ticket.append({"type": "text", "value": f"SIRET: {ticket_data['business_siret']}"})
        if ticket_data['business_vat_number']:
            ticket.append({"type": "text", "value": f"TVA: {ticket_data['business_vat_number']}"})

        ticket.extend([
            {"type": "line", "value": "single"},  # Wider separator for 80mm
            {"type": "align", "value": "left"},
            {"type": "text", "value": f"DATE: {ticket_data['date_time']}"},
            {"type": "text", "value": f"TICKET: {ticket_data['receipt_id']}"},
        ])

        if ticket_data['table']:
            ticket.append({"type": "text", "value": f"TABLE: {remove_accents(ticket_data['table'])}"})
        if ticket_data['server']:
            ticket.append({"type": "text", "value": f"SERVEUR: {remove_accents(ticket_data['server'])}"})

        ticket.append({"type": "line", "value": "single"})

        # Add articles with more detailed formatting
        ticket.append({"type": "text", "value": "ARTICLE               QTE       PRIX    TOTAL"})
        ticket.append({"type": "line", "value": "single"})

        for article in ticket_data['articles']:
            name = remove_accents(article['name'])
            qty = article['quantity']
            price = article['unit_price']
            total = article['total_price']

            # Truncate name if too long
            if len(name) > 20:
                name = name[:17] + "..."

            # Format with fixed width columns
            ticket.append({"type": "text", "value": f"{name.ljust(20)} {str(qty).ljust(6)} {price}  {total}"})

        # Add totals
        ticket.extend([
            {"type": "line", "value": "single"},
            {"type": "align", "value": "right"},
            {"type": "text", "value": f"TOTAL HT: {ticket_data['total_ht']}"},
            {"type": "text", "value": f"TVA: {ticket_data['total_tva']}"},
            {"type": "bold", "value": 1},
            {"type": "text", "value": f"TOTAL TTC: {ticket_data['total_ttc']}"},
            {"type": "bold", "value": 0},
            {"type": "align", "value": "left"},
            {"type": "text", "value": f"PAIEMENT: {remove_accents(ticket_data['payment_method'])}"},
        ])

        # Add footer
        ticket.extend([
            {"type": "line", "value": "single"},
            {"type": "align", "value": "center"},
        ])

        if ticket_data['footer']:
            ticket.append({"type": "text", "value": remove_accents(ticket_data['footer'])})

        # Add final commands
        ticket.extend([
            {"type": "feed", "value": 3},
            {"type": "cut"},
        ])

        # Send the ticket to the printer
        send_print_order_inner_sunmi.delay(ws_channel, ticket)
        logger.info(f"Receipt printed to Sunmi 80mm printer: {printer.name}")
        return True

    except Exception as e:
        logger.error(f"Error printing to Sunmi 80mm printer {printer.name}: {e}")
        traceback.print_exc()
        return False

def print_ticket_purchases_sunmi_cloud(ticket_data, printer, size=80):
    """
    Print a purchase receipt to a Sunmi Cloud printer.

    Args:
        ticket_data (dict): The ticket data dictionary
        printer (Printer): The printer object
        size (int): The printer size in mm (57 or 80)

    Returns:
        bool: True if the print job was successfully sent, False otherwise
    """
    from .views import remove_accents

    try:
        # Get the printer's serial number
        printer_sn = printer.sunmi_serial_number
        if not printer_sn:
            logger.error(f"Printer {printer.name} has no serial number")
            return False

        # Get the Sunmi Cloud Printer credentials from the Configuration
        try:
            config = Configuration.get_solo()
            app_id = config.get_sunmi_app_id()
            app_key = config.get_sunmi_app_key()
        except Exception as e:
            logger.error(f"Failed to get Sunmi Cloud Printer credentials: {e}")
            return False

        # Create a printer instance with dots per line based on size
        dots_per_line = 384 if size == 80 else 240  # 384 for 80mm, 240 for 57mm
        from .sunmi_cloud_printer import SunmiCloudPrinter, ALIGN_CENTER, ALIGN_LEFT, ALIGN_RIGHT
        printer = SunmiCloudPrinter(dots_per_line, app_id=app_id, app_key=app_key, printer_sn=printer_sn)

        # Add header
        printer.lineFeed()
        printer.setAlignment(ALIGN_CENTER)
        printer.setPrintModes(True, True, True)  # Bold, double height, double width
        printer.appendText(remove_accents(ticket_data['business_name'].upper()) + "\n")
        printer.setPrintModes(False, False, False)  # Reset print modes

        # Add business information
        if ticket_data['business_address'] and ticket_data['business_address'] != 'None':
            printer.appendText(remove_accents(ticket_data['business_address']) + "\n")
        if ticket_data['business_siret']:
            printer.appendText(f"SIRET: {ticket_data['business_siret']}\n")
        if ticket_data['business_vat_number']:
            printer.appendText(f"TVA: {ticket_data['business_vat_number']}\n")

        # Add separator
        printer.appendText("-" * (48 if size == 80 else 32) + "\n")

        # Add receipt information
        printer.setAlignment(ALIGN_LEFT)
        printer.appendText(f"DATE: {ticket_data['date_time']}\n")
        printer.appendText(f"TICKET: {ticket_data['receipt_id']}\n")

        if ticket_data['table']:
            printer.appendText(f"TABLE: {remove_accents(ticket_data['table'])}\n")
        if ticket_data['server']:
            printer.appendText(f"SERVEUR: {remove_accents(ticket_data['server'])}\n")

        # Add separator
        printer.appendText("-" * (48 if size == 80 else 32) + "\n")

        # Add articles
        if size == 80:
            printer.appendText("ARTICLE                  QTE    PRIX    TOTAL\n")
            printer.appendText("-" * 48 + "\n")

            for article in ticket_data['articles']:
                name = remove_accents(article['name'])
                qty = article['quantity']
                price = article['unit_price']
                total = article['total_price']

                # Truncate name if too long
                if len(name) > 20:
                    name = name[:17] + "..."

                # Format with fixed width columns
                printer.appendText(f"{name.ljust(20)} {str(qty).ljust(6)} {price}  {total}\n")
        else:
            # For 57mm, use a simpler format
            for article in ticket_data['articles']:
                name = remove_accents(article['name'])
                qty = article['quantity']
                price = article['unit_price']
                total = article['total_price']

                printer.appendText(name + "\n")
                printer.appendText(f"{qty} x {price} = {total}\n")

        # Add separator
        printer.appendText("-" * (48 if size == 80 else 32) + "\n")

        # Add totals
        printer.setAlignment(ALIGN_RIGHT)
        printer.appendText(f"TOTAL HT: {ticket_data['total_ht']}\n")
        printer.appendText(f"TVA: {ticket_data['total_tva']}\n")
        printer.setPrintModes(True, False, False)  # Bold
        printer.appendText(f"TOTAL TTC: {ticket_data['total_ttc']}\n")
        printer.setPrintModes(False, False, False)  # Reset print modes

        printer.setAlignment(ALIGN_LEFT)
        printer.appendText(f"PAIEMENT: {remove_accents(ticket_data['payment_method'])}\n")

        # Add footer
        printer.appendText("-" * (48 if size == 80 else 32) + "\n")
        printer.setAlignment(ALIGN_CENTER)

        if ticket_data['footer']:
            printer.appendText(remove_accents(ticket_data['footer']) + "\n")

        # Add final commands
        printer.lineFeed(3)
        printer.cut()

        # Send the print job
        printer.printData()
        logger.info(f"Receipt printed to Sunmi Cloud {size}mm printer: {printer.name}")
        return True

    except Exception as e:
        logger.error(f"Error printing to Sunmi Cloud printer {printer.name}: {e}")
        traceback.print_exc()
        return False

@app.task
def test_print(printer_pk):
    """
    Print a test message using the specified printer type and ticket size.

    Args:
        printer_type (str): The type of printer to use. Must be one of:
            - 'EP' for Epson via Serveur sur Pi (réseau ou USB)
            - 'S8' for Sunmi integrated 80mm
            - 'S5' for Sunmi integrated 57mm
            - 'SC' for Sunmi Cloud printer
        ticket_size (int): The size of the ticket in mm. Default is 80.
            Only used for Sunmi Cloud printer. Valid values are 80 and 57.

    Returns:
        bool: True if the test print was successful, False otherwise
    """
    from .models import Printer
    printer = Printer.objects.get(pk=printer_pk)
    printer_type = printer.printer_type


    logger.info(f"Test print for printer type {printer_type}")

    try:
        # Validate printer type
        if printer_type not in [Printer.EPSON_PI, Printer.SUNMI_INTEGRATED_80, 
                               Printer.SUNMI_INTEGRATED_57, Printer.SUNMI_CLOUD]:
            logger.error(f"Invalid printer type: {printer_type}")
            return False

        # Handle Epson TM20 printer
        if printer_type == Printer.EPSON_PI:

            req = requests.session()
            try:
                # Pour serveur sous flask :
                reponse = req.post(f'{printer.serveur_impression}',
                                   data={
                                       'coucouapi': printer.api_serveur_impression,
                                       'adresse_printer': printer.thermal_printer_adress,
                                       'copy': '1',
                                       'title': "*** TEST PRINT ***",
                                       'header': "Hello World",
                                       'body': "",
                                       'footer': f"Test completed at {time.strftime('%Y-%m-%d %H:%M:%S')}",
                                   })
                logger.info(f"REPONSE Serveur impression : {reponse.status_code} - {reponse.text}")
            except ConnectionError:
                logger.error(f"print_command ConnectionError for {printer.thermal_printer_adress} ")
            except Exception as e:
                logger.error(f"print_command Exception for {printer.thermal_printer_adress} : {e}")

            req.close()
            return True

        # Handle Sunmi integrated printers
        elif printer_type in [Printer.SUNMI_INTEGRATED_80, Printer.SUNMI_INTEGRATED_57]:
            # For testing purposes, we need a WebSocket channel
            # In a real scenario, this would come from a Printer instance
            ws_channel = printer.host.user.uuid.hex

            # Create a simple test ticket
            ticket = [
                {"type": "font", "value": "A"},
                {"type": "size", "value": 1},
                {"type": "bold", "value": 1},
                {"type": "align", "value": "left"},
                {"type": "text", "value": "** TEST PRINT FROM ADMIN **"},
                {"type": "bold", "value": 0},
                {"type": "text", "value": "Hello World admin"},
                {"type": "size", "value": 0},
                {"type": "text", "value": "--------------------------------"},
                {"type": "text", "value": f"Test completed at {time.strftime('%Y-%m-%d %H:%M:%S')}"},
                {"type": "feed", "value": 2},
                {"type": "cut"},
            ]

            # Send the print job
            send_print_order_inner_sunmi.delay(ws_channel, ticket)
            logger.info("Test print sent to Sunmi integrated printer")
            return True

        # Handle Sunmi Cloud printer
        elif printer_type == Printer.SUNMI_CLOUD:
            # For testing purposes, we need app_id, app_key, and printer_sn
            # In a real scenario, these would come from a Printer instance and Configuration
            try:
                from APIcashless.models import Configuration
                config = Configuration.objects.get()
                app_id = config.get_sunmi_app_id()
                app_key = config.get_sunmi_app_key()

                # For testing, we need a printer serial number
                # In a real scenario, this would come from a Printer instance
                # Here we'll use a placeholder
                printer_sn = printer.sunmi_serial_number

                # Set dots_per_line based on ticket size
                dots_per_line = 384

                # Create a printer instance
                printer = SunmiCloudPrinter(dots_per_line, app_id=app_id, app_key=app_key, printer_sn=printer_sn)

                # Create a simple test receipt
                printer.lineFeed()
                printer.setAlignment(ALIGN_CENTER)
                printer.setPrintModes(True, True, False)  # Bold, double height, normal width
                printer.appendText("*** TEST PRINT FROM ADMIN ***\n")
                printer.setPrintModes(False, False, False)  # Reset print modes
                printer.appendText("Hello World\n")
                printer.appendText("------------------------\n")
                printer.setAlignment(ALIGN_LEFT)
                printer.appendText(f"Ticket Size: 80mm\n")
                printer.appendText(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                printer.lineFeed(3)
                printer.cutPaper(False)  # Partial cut

                # Generate a unique trade number for this print job
                trade_no = f"test_{int(time.time())}"

                # Send the print job to the printer
                printer.pushContent(
                    trade_no=trade_no,
                    sn=printer_sn,
                    count=1,
                    media_text="Test Print"
                )

                logger.info(f"Test print sent to Sunmi Cloud Printer")
                return True

            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error in test_print for Sunmi Cloud Printer: {e}")
                return False

    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error in test_print: {e}")
        return False

@app.task
def print_command_sunmi_cloud(commande, groupe, lignes_article):
    """
    Print a command ticket using the Sunmi Cloud Printer.

    Args:
        commande: The CommandeSauvegarde object
        groupe: The GroupementCategorie object
        lignes_article: List of article lines to print

    Returns:
        bool: True if the print job was successfully sent, False otherwise
    """
    try:
        # Check if the printer is a Sunmi Cloud Printer
        if not groupe.printer or groupe.printer.printer_type != groupe.printer.SUNMI_CLOUD:
            logger.error(f"Printer for group {groupe.name} is not a Sunmi Cloud Printer")
            return False

        # Get the printer's serial number
        printer_sn = groupe.printer.sunmi_serial_number
        if not printer_sn:
            logger.error(f"Printer {groupe.printer.name} has no serial number")
            return False

        # Get the Sunmi Cloud Printer credentials from the Configuration
        try:
            config = Configuration.objects.get()
            app_id = config.get_sunmi_app_id()
            app_key = config.get_sunmi_app_key()
        except Exception as e:
            logger.error(f"Failed to get Sunmi Cloud Printer credentials: {e}")
            return False

        # Determine the ticket number
        numero = commande.numero_du_ticket_imprime.get(groupe.name)
        if numero:
            title = f"{groupe.name} {numero}"
        else:
            groupe.compteur_ticket_journee += 1
            commande.numero_du_ticket_imprime[groupe.name] = groupe.compteur_ticket_journee
            groupe.save()
            commande.save()
            title = f"{groupe.name} {groupe.compteur_ticket_journee}"

        # Create a printer instance with 384 dots per line (standard for 80mm thermal printer)
        printer = SunmiCloudPrinter(384, app_id=app_id, app_key=app_key, printer_sn=printer_sn)

        # Increase general font size for better visibility
        printer.setCharacterSize(2, 2)  # Increase both height and width

        # Add header information
        printer.lineFeed()
        printer.setAlignment(ALIGN_CENTER)
        printer.setPrintModes(True, True, True)  # Bold, double height, double width
        printer.appendText(f"{title}\n")
        printer.setPrintModes(False, False, False)  # Reset print modes

        # Add command information
        printer.setAlignment(ALIGN_LEFT)
        printer.appendText(f"Date: {commande.datetime.astimezone().strftime('%d/%m/%Y %H:%M')}\n")
        printer.setPrintModes(True, True, True)  # Bold
        printer.appendText(f"TABLE: {commande.table.name}\n")
        printer.setPrintModes(False, False, False)  # Reset print modes
        printer.appendText(f"Serveur: {commande.responsable.name}\n")
        printer.appendText(f"ID: {commande.id_commande()[:3]}\n")
        printer.appendText("-" * 40 + "\n")  # Increase separator width to use full 80mm

        # Add article lines with enhanced visibility - even larger and wider
        printer.setCharacterSize(3, 3)  # Increase size specifically for articles (larger than general 2x2)
        printer.setPrintModes(True, True, True)  # Bold, double height, AND double width for maximum visibility
        for ligne in lignes_article:
            printer.appendText(f"{int(ligne.qty)} x {ligne.article.name}\n")
        printer.setPrintModes(False, False, False)  # Reset print modes
        printer.setCharacterSize(2, 2)  # Reset back to general size

        # Add footer and cut paper
        printer.appendText("-" * 40 + "\n")  # Increase separator width to use full 80mm
        printer.lineFeed(6)  # Add more whitespace before cutting
        printer.cutPaper(False)  # Partial cut

        # Generate a unique trade number for this print job
        trade_no = f"{printer_sn}_{int(time.time())}"

        # Send the print job to the printer
        printer.pushContent(
            trade_no=trade_no,
            sn=printer_sn,
            count=1,
            media_text=title
        )

        logger.info(f"Print job sent to Sunmi Cloud Printer {printer_sn} for {title}")
        return True
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error in print_command_sunmi_cloud: {e}")
        return False
