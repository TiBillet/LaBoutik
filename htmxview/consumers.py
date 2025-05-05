# chat/consumers.py
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.template.loader import get_template
from django.utils import timezone
from nose.tools import raises

logger = logging.getLogger(__name__)




class PrintConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.user = self.scope['user']

        # Si l'user n'est pas un terminal préalablement appairé :
        if not settings.DEBUG:
            if not self.user.is_authenticated or not hasattr(self.user, 'appareil'):
                logger.error(f"{self.room_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")
                raise Exception(f"{self.room_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")


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

