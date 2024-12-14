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
        self.room_group_name = 'chat_%s' % self.room_name
        self.user = self.scope['user']

        # Si l'user n'est pas un terminal préalablement appairé :
        if not settings.DEBUG:
            if not self.user.is_authenticated or not hasattr(self.user, 'appareil'):
                logger.error(f"{self.room_name} {self.room_group_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")
                raise Exception(f"{self.room_name} {self.room_group_name} {self.user} ERROR NOT AUTHENTICATED OR NOT APPAREIL")

        logger.info(f"{self.room_name} {self.room_group_name} {self.user} connected")

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': f"{self.user} : {message}"
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))


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

