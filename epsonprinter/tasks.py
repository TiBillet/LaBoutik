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

# Dictionary to store printer responses
printer_responses = {}

def handle_printer_response(message):
    """
    Handle a response from the printer.

    This function should be called by the websocket consumer when a response is received from the printer.
    The expected format of the response is "print ok <uuid>", where <uuid> is the UUID of the print order.

    Example usage in a consumer:

    ```python
    # In the consumer's receive method
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')

        # If the message is a printer response (starts with "print ok ")
        if message.startswith("print ok "):
            # Import and call the handle_printer_response function
            from epsonprinter.tasks import handle_printer_response
            handle_printer_response(message)
    ```

    Args:
        message (str): The message received from the printer, expected format: "print ok <uuid>"

    Returns:
        bool: True if the response was successfully handled, False otherwise
    """
    try:
        # Parse the message to extract the UUID
        if message.startswith("print ok "):
            uuid_str = message[9:]  # Extract the UUID part (after "print ok ")
            logger.info(f"Received printer response for UUID: {uuid_str}")

            # Store the response in the dictionary
            printer_responses[uuid_str] = message
            return True
        else:
            logger.warning(f"Received unexpected printer response format: {message}")
            return False
    except Exception as e:
        logger.error(f"Error handling printer response: {e}")
        return False


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
    MAX_RETRY_TIME = 60 * 60 * 1  # seconds

    # Generate a unique UUID for this print order
    order_uuid = uuid.uuid4()

    logger.info(f"HTTP Print/test_groupe : tentative d'envoi de message vers WS sur le canal {ws_channel}")
    try:

        # Send the message to the websocket channel
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            ws_channel,
            {
                'type': 'chat_message',
                'message': f'print_order@{order_uuid}',
                'data': data,
                'uuid': order_uuid,  # Include the UUID separately for easier access
            }
        )
        logger.info(f"HTTP Print/test_groupe : message envoyé avec succès vers WS sur le canal {ws_channel} avec UUID {order_uuid}")

        #TODO: Checker la réponse et raise une erreur pour retry
        response_received = True
        return True

    except Exception as exc:
        logger.error(f"WS : erreur lors de l'envoi du message vers WS sur le canal {ws_channel}: {exc}")
        # Ajoute un backoff exponentiel pour les autres erreurs
        retry_delay = min(2 ** self.request.retries, MAX_RETRY_TIME)
        raise self.retry(exc=exc, countdown=retry_delay)
    except MaxRetriesExceededError:
        logger.error(f"send_print_order : La tâche a échoué après plusieurs tentatives pour {order_uuid}")


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
