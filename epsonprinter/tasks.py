from time import sleep

from django.utils import timezone

from APIcashless.models import CommandeSauvegarde, GroupementCategorie, ArticleVendu, Articles
from Cashless.celery import app
import logging

from .views import print_command, article_direct_to_printer, TicketZ_PiEpson_Printer

logger = logging.getLogger(__name__)


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