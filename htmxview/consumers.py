# chat/consumers.py
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.template.loader import get_template
from django.utils import timezone

logger = logging.getLogger(__name__)




class PrintConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.user = self.scope['user']

        # Si l'user n'est pas un terminal préalablement appairé :
        if not settings.DEBUG:
            if not self.user.is_authenticated or not hasattr(self.user, 'appareil'):
                logger.error(f"{self.room_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")
                # On ferme proprement le websocket au lieu de lever une exception.
                # / Cleanly close the socket instead of raising.
                await self.close()
                return


        # Join room group
        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )

        logger.info(f"channel_name : {self.channel_name} - room : {self.room_name} - user : {self.user} connected")
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        logger.info(f"receive : {text_data}")
        text_data_json = json.loads(text_data)

        # Send message to room group
        # La fonction correspondant à type s'occupe de créer le html
        await self.channel_layer.group_send(
            self.room_name,
            # ce dictionnaire est event
            {
                'type': 'notification',
                'user': f"{self.user}",
                'message': f"Nouveau message"
            }
        )

    # Receive message from room group to a printer
    async def from_ws_to_printer(self, event):
        logger.info(f"from_ws_to_printer event: {event}")
        data = {
            'type' : f'printer',
            'message' : f'{event.get("message")}'
        }
        # Envoie sur le canal room_name le json
        await self.send(text_data=json.dumps(data))

    # Receive message from room group
    # Doit avoir le même nom que le type du message de la methode receive
    async def notification(self, event):
        logger.info(f"notification event: {event}")
        html = get_template("print/notification.html").render(context={'event': event})
        # Send message to WebSocket htmx
        await self.send(text_data=html)



class TerminalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.user = self.scope['user']

        # Si l'appareil n'est pas appairé : on ferme proprement le websocket
        # au lieu de lever une exception (qui laissait un traceback inutile).
        # / Device not paired: cleanly close the socket instead of raising.
        if not settings.DEBUG:
            if not self.user.is_authenticated or not hasattr(self.user, 'appareil'):
                logger.error(f"{self.room_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")
                await self.close()
                return

        logger.info(f"{self.room_name} {self.user} connected")

        # Join room group
        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )

        await self.accept()

        # REJEU D'ETAT A LA (RE)CONNEXION
        # / State replay on (re)connect
        #
        # Le resultat final du paiement (succes/annule) est pousse une seule fois
        # par la tache Celery `poll_payment_intent_status`.
        # Si le reseau de la borne coupe juste a cet instant, ou si le paiement
        # reussit avant meme que ce websocket soit connecte, le message est perdu :
        # l'ecran reste bloque sur le spinner alors que Stripe a deja valide.
        #
        # Pour eviter ca : des qu'un client (re)connecte, on relit l'etat reel du
        # paiement en base. S'il est deja termine, on lui renvoie tout de suite le
        # bon ecran. La tache Celery met l'etat a jour en base meme quand la borne
        # est deconnectee, donc l'etat lu ici est fiable.
        #
        # / The final payment result is pushed only once by the Celery task and can
        # be lost on a flaky network. On reconnect we re-read the real status from
        # the database and replay the correct screen.
        await self.replay_payment_state_if_finished()

    @database_sync_to_async
    def get_finished_template_name(self):
        """
        Lit le statut reel du paiement en base et renvoie le nom du template final
        si le paiement est termine, sinon None.
        / Reads the real payment status from DB; returns the final template name
        if the payment is finished, else None.

        room_name == payment_intent_stripe_id
        (voir routing.py et kiosk/waiting_credit_card_terminal.html)
        """
        from APIcashless.models import PaymentsIntent
        try:
            payment_intent = PaymentsIntent.objects.get(payment_intent_stripe_id=self.room_name)
        except PaymentsIntent.DoesNotExist:
            return None

        if payment_intent.status == PaymentsIntent.SUCCEEDED:
            return 'success.html'
        if payment_intent.status == PaymentsIntent.CANCELED:
            return 'cancel.html'
        # Paiement encore en cours : le polling enverra la suite.
        # / Still in progress: polling will send the rest.
        return None

    async def replay_payment_state_if_finished(self):
        """
        Renvoie immediatement l'ecran final (succes/annule) si le paiement est
        deja termine au moment ou ce client (re)connecte. Sinon ne fait rien.
        / Immediately replays the final screen if the payment is already finished.
        """
        template_name = await self.get_finished_template_name()
        if not template_name:
            return
        logger.info(f"Rejeu d'etat WS pour {self.room_name} -> kiosk/{template_name}")
        # Meme rendu que la methode `template()` : le HTML porte un hx-swap-oob
        # qui remplace #tb-kiosque cote borne.
        # / Same render as `template()`: the HTML carries an hx-swap-oob.
        html = get_template(f"kiosk/{template_name}").render(context={})
        await self.send(text_data=html)

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        logger.info(f"receive : {text_data}")
        text_data_json = json.loads(text_data)
        amount = text_data_json['amount']


        # Send message to room group
        # La fonction correspondant à type s'occupe de créer le html
        await self.channel_layer.group_send(
            self.room_name,
            # ce dictionnaire est event
            {
                'type': 'notification',
                'user': f"{self.user}",
                'notification': f"Nouveau message"
            }
        )


    # Receive message from room group
    # Doit avoir le même nom que le type du message de la methode receive
    async def template(self, event):
        logger.info(f"template event: {event}")
        template_name = event['template']

        html = get_template(f"kiosk/{template_name}").render(context={'event': event})
        # Send message to WebSocket htmx
        await self.send(text_data=html)



    # Receive message from room group
    # Doit avoir le même nom que le type du message de la methode receive
    async def notification(self, event):
        logger.info(f"notification event: {event}")
        html = get_template("tpe/notification.html").render(context={'event': event})
        # Send message to WebSocket htmx
        await self.send(text_data=html)


    # Receive message from room group
    # Doit avoir le même nom que le type du message de la methode receive
    async def message(self, event):
        logger.info(f"message event: {event}")
        html = get_template("tpe/message.html").render(context={'event': event})
        # Send message to WebSocket htmx
        await self.send(text_data=html)




# Pour TUTO JS
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        try :
            self.user = self.scope['user']
            # Utilisation de l'ip de l'appareil comme room name websocket
            self.room_group_name = self.user.uuid.hex # hex car il ne faut pas de tiret dans le nom
        except Exception as e:
            logger.error(f"consumer connect error {e}")
            await self.close()
            return False

        # Si l'user n'est pas un terminal préalablement appairé :
        if not settings.DEBUG:
            if not self.user.is_authenticated or not hasattr(self.user, 'appareil'):
                logger.error(f"{self.room_name} {self.room_group_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")
                raise Exception(f"{self.room_name} {self.room_group_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")

        logger.info(f"CONNECT ChatConsumer room_name / room_group_name: {self.room_name} / {self.room_group_name} \n"
                    f"self.user : {self.user} - authenticated : {self.user.is_authenticated}\n"
                    f"appareil : {hasattr(self.user, 'appareil')}\n")

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name, # Nom du canal de chaque appareil
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        try :
            logger.info(f"{self.room_name} {self.user} disconnected")
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            logger.error(f"consumer disconnect error {e}")
            await self.close()
            return False

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        logger.info(f"receive : {text_data}")

        message = text_data_json['message']

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    # Called when server sends a message to device's group, triggered by 'chat_message' type
    async def chat_message(self, event):
        """
        Handles messages sent from server to device WebSocket.
        
        The server sends a message using:
        async_to_sync(channel_layer.group_send)(
            "<device_id>",  # Group name is device ID
            {
                'type': 'chat_message',     # Triggers this handler
                'message': 'print_command',  # Command to execute
                'data': [                    # Print job data
                    {"type": "barcode", "value": "1234567890456"},
                    {"type": "qrcode", "value": "https://tibillet.org/"}
                ],
            }
        )
        
        Args:
            event (dict): Contains message and data payload sent by server
                         data format: list of print commands as dicts
        """
        
        inputContent = event['message']
        ticket = event['data']
        user = self.user
        logger.info(f"chat_message \ninputContent: {inputContent} \nticket: {ticket} \nuser: {user} \nend chat_message \n")
        
        await self.send(text_data=json.dumps({
            'message': 'print',
            'data': ticket,
            # 'user': f"{user}"
        }))


        ''' 
        exemple :
        ticket = [
            {"type": "text", "value": "--------------------------------"},
            {"type": "align", "value": "center"},
            {"type": "image", "value": "https://laboutik.filaos.re/static/webview/images/logoTicket.png"},
            {"type": "font", "value": "A"},
            {"type": "size", "value": 1},
            {"type": "bold", "value": 1},
            {"type": "text", "value": "Titre"},
            {"type": "bold", "value": 0},
            {"type": "size", "value": 0},
            {"type": "barcode", "value": "1234567890456"},
            {"type": "qrcode", "value": "https://tibillet.org/"},
            {"type": "text", "value": "---- fin ----"},
            {"type": "feed", "value": 3},
            {"type": "cut"}
        ]
        '''

# Pour TUTO HTMX
class HtmxConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.user = self.scope['user']

        # Si l'user n'est pas un terminal préalablement appairé :
        if not settings.DEBUG:
            if not self.user.is_authenticated or not hasattr(self.user, 'appareil'):
                logger.error(f"{self.room_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")
                raise Exception(f"{self.room_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")

        logger.info(f"{self.room_name} {self.user} connected")

        # Join room group
        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        logger.info(f"receive : {text_data}")
        text_data_json = json.loads(text_data)
        message = text_data_json['message']


        # Send message to room group
        # La fonction correspondant à type s'occupe de créer le html
        await self.channel_layer.group_send(
            self.room_name,
            # ce dictionnaire est event
            {
                'type': 'notification',
                'user': f"{self.user}",
                'notification': f"Nouveau message"
            }
        )

        # Send another message for exemple
        await self.channel_layer.group_send(
            self.room_name,
            # ce dictionnaire est event
            {
                'type': 'message',
                'user': f"{self.user}",
                'message': f"{message}"
            }
        )


    # Receive message from room group
    # Doit avoir le même nom que le type du message de la methode receive
    async def notification(self, event):
        logger.info(f"notification event: {event}")
        html = get_template("websocket/tuto_htmx/notification.html").render(context={'event': event})
        # Send message to WebSocket htmx
        await self.send(text_data=html)


    # Receive message from room group
    # Doit avoir le même nom que le type du message de la methode receive
    async def message(self, event):
        logger.info(f"message event: {event}")
        html = get_template("websocket/tuto_htmx/message.html").render(context={'event': event})
        # Send message to WebSocket htmx
        await self.send(text_data=html)

