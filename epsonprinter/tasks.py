import uuid
import time
import traceback
from time import sleep

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from channels.layers import get_channel_layer
from django.utils import timezone

from APIcashless.models import CommandeSauvegarde, GroupementCategorie, ArticleVendu, Articles, Configuration
from Cashless.celery import app
import logging
from asgiref.sync import async_to_sync

from .views import print_command, article_direct_to_printer, TicketZ_PiEpson_Printer
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
        commande = CommandeSauvegarde.objects.get(pk=commande_pk)

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
                    # For Epson printers, we need to pass the whole command and optionally the groupement
                    result = print_command_epson_tm20(commande, groupe if groupement_solo else None)
                elif printer_type in [groupe.printer.SUNMI_INTEGRATED_80, groupe.printer.SUNMI_INTEGRATED_57]:
                    # For Sunmi integrated printers
                    result = print_command_inner_sunmi(commande, groupe, lignes_article)
                elif printer_type == groupe.printer.SUNMI_CLOUD:
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

    # Header contenant les infos générales
    base_ticket = [
        {"type": "size", "value": 0},
        {"type": "text", "value": "-" * 32},
        {"type": "size", "value": 1},
        {"type": "text", "value": f"{commande.datetime.astimezone().strftime('%d/%m/%Y %H:%M')}"},
        {"type": "bold", "value": 1},
        {"type": "text", "value": f"TABLE : {commande.table.name}"},
        {"type": "bold", "value": 0},
        {"type": "text", "value": f"{commande.responsable.name}"},
        {"type": "text", "value": f"ID : {commande.id_commande()[:3]}"},
        {"type": "size", "value": 0},
        {"type": "text", "value": "-" * 32},
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
        {"type": "align", "value": "center"},
        {"type": "text", "value": f"{title}"},
        {"type": "align", "value": "left"},
    ]
    for ligne in lignes_article:
        ticket.append({"type": "text", "value": f"{int(ligne.qty)} x {ligne.article.name}"}, )

    ticket += [
        {"type": "size", "value": 0},
        {"type": "text", "value": "-" * 32},
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
    logger.info(f"PRINT : Celery print_command_epsonTM20 : {commande} - {groupement_solo}")

    ticket = print_command(commande, groupement_solo)

    if ticket.can_print():
        logger.info(f"   ticket.can_print() -> PRINT")
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
def test_print(printer_pk, ticket_size=80):
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

    logger.info(f"Test print for printer type {printer_type} with ticket size {ticket_size}mm")

    try:
        # Validate printer type
        if printer_type not in [Printer.EPSON_PI, Printer.SUNMI_INTEGRATED_80, 
                               Printer.SUNMI_INTEGRATED_57, Printer.SUNMI_CLOUD]:
            logger.error(f"Invalid printer type: {printer_type}")
            return False

        # Validate ticket size
        if ticket_size not in [80, 57]:
            logger.error(f"Invalid ticket size: {ticket_size}. Must be 80 or 57.")
            return False

        # Handle Epson TM20 printer
        if printer_type == Printer.EPSON_PI:
            from .views import print_command

            # Create a simple test ticket
            test_ticket = print_command(None)
            test_ticket.header = ["*** TEST PRINT ***", "Hello World"]
            test_ticket.body = []
            test_ticket.footer = [f"Test completed at {time.strftime('%Y-%m-%d %H:%M:%S')}"]

            # Print the ticket
            test_ticket.to_printer()
            logger.info("Test print sent to Epson TM20 printer")
            return True

        # Handle Sunmi integrated printers
        elif printer_type in [Printer.SUNMI_INTEGRATED_80, Printer.SUNMI_INTEGRATED_57]:
            # For testing purposes, we need a WebSocket channel
            # In a real scenario, this would come from a Printer instance
            ws_channel = printer.user.uuid.hex

            # Create a simple test ticket
            ticket = [
                {"type": "font", "value": "A"},
                {"type": "size", "value": 1},
                {"type": "bold", "value": 1},
                {"type": "align", "value": "center"},
                {"type": "text", "value": "*** TEST PRINT ***"},
                {"type": "bold", "value": 0},
                {"type": "text", "value": "Hello World"},
                {"type": "align", "value": "left"},
                {"type": "size", "value": 0},
                {"type": "text", "value": "-" * 32},
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
                dots_per_line = 384 if ticket_size == 80 else 274

                # Create a printer instance
                printer = SunmiCloudPrinter(dots_per_line, app_id=app_id, app_key=app_key, printer_sn=printer_sn)

                # Create a simple test receipt
                printer.lineFeed()
                printer.setAlignment(ALIGN_CENTER)
                printer.setPrintModes(True, True, False)  # Bold, double height, normal width
                printer.appendText("*** TEST PRINT ***\n")
                printer.setPrintModes(False, False, False)  # Reset print modes
                printer.appendText("Hello World\n")
                printer.appendText("------------------------\n")
                printer.setAlignment(ALIGN_LEFT)
                printer.appendText(f"Ticket Size: {ticket_size}mm\n")
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

                logger.info(f"Test print sent to Sunmi Cloud Printer with {ticket_size}mm ticket")
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
        printer.setPrintModes(True, False, False)  # Bold
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
