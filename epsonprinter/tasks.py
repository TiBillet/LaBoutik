import uuid
import time
from time import sleep

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from channels.layers import get_channel_layer
from django.utils import timezone

from APIcashless.models import CommandeSauvegarde, GroupementCategorie, ArticleVendu, Articles
from Cashless.celery import app
import logging
from asgiref.sync import async_to_sync

from .views import print_command, article_direct_to_printer, TicketZ_PiEpson_Printer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=10)
def send_print_order(self, ws_channel, data):
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
        logger.info(f"send_print_order : message envoyé avec succès vers WS sur le canal {ws_channel} avec UUID {order_uuid}")

        #TODO: Checker la réponse et raise une erreur pour retry
        response_received = True
        return True

    except Exception as exc:
        # Ajoute un backoff exponentiel pour les autres erreurs
        retry_delay = min(2 ** self.request.retries, MAX_RETRY_TIME)
        logger.error(f"WS : erreur lors de l'envoi du message vers WS sur le canal {ws_channel}: {exc}\n next retry in {retry_delay} seconds...")
        raise self.retry(exc=exc, countdown=retry_delay)
    except MaxRetriesExceededError:
        logger.error(f"send_print_order : La tâche a échoué après plusieurs tentatives pour {order_uuid}")
        return False


@app.task
def print_command_sunmi(commande_pk):
    commande = CommandeSauvegarde.objects.get(pk=commande_pk)

    # Header contenant les infos générales
    base_ticket = [
        {"type": "text", "value": "-" * 32},
        {"type": "text", "value": f"{commande.datetime}"},
        {"type": "text", "value": f"TABLE : {commande.table.name}"},
        {"type": "text", "value": f"RESPONSABLE : {commande.responsable.name}"},
        {"type": "text", "value": f"ID COMMANDE : {commande.id_commande()[:3]}"},
        # {"type": "text", "value": f"SERVICE : {commande.id_service()[:3]}"},
        {"type": "text", "value": "-" * 32},
    ]
    # L'objet GroupementCategorie regroupe les catégories
    groupements = GroupementCategorie.objects.all()

    # Les articles possèdent des catégories :
    lignes_articles = commande.articles.all()

    # On veut un dictionnaire avec {GROUPEMENT:[article1, articles2]}
    articles_groupe = {}
    for groupement in groupements:
        articles_groupe[groupement] = []
        categories_groupees = groupement.categories.all()
        for ligne_article in lignes_articles:
            if ligne_article.article.categorie in categories_groupees:
                articles_groupe[groupement].append(ligne_article)

    # Ajouter chaque groupe d'articles au ticket
    for groupe, lignes_article in articles_groupe.items():
        if len(lignes_article) > 0 and groupe.printer:
            if groupe.printer.host:
                if groupe.printer.host.user :
                    ws_channel = groupe.printer.host.user.uuid.hex
                    # fabrication du ticket en envoi à l'imprimante
                    ticket = []
                    ticket.append({"type": "text", "value": f"{groupe.name}"})  # Le nom de la catégorie. ex : CUISINE
                    for ligne in lignes_article:
                        ticket.append({"type": "text", "value": f"{int(ligne.qty)} x {ligne.article.name}"}, )

                    ticket += [{"type": "text", "value": "-" * 32},
                               {"type": "feed", "value": 2},
                               {"type": "cut"},
                               ]
                    send_print_order.delay(ws_channel, ticket)


            logger.info(ticket)

    return True

@app.task
def print_command_epson_tm20(commande_pk, groupement_solo_pk=None):

    commande = CommandeSauvegarde.objects.get(pk=commande_pk)
    groupement_solo = None
    if groupement_solo_pk:
        groupement_solo = GroupementCategorie.objects.get(pk=groupement_solo_pk)

    logger.info(f"PRINT : Celery print_command_epsonTM20 : {commande} - {groupement_solo}")

    ticket = print_command(commande, groupement_solo)

    if ticket.can_print():
        logger.info(f"   ticket.can_print() -> PRINT")
        #TODO: Tester max retry avec le débranchage de l'imprimante
        ticket.to_printer()



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
    else :
        print(ticket_Z._header())
        print(ticket_Z._body())
        print(ticket_Z._footer())
