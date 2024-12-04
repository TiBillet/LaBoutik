# chat/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from nose.tools import raises

logger = logging.getLogger(__name__)

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


class StripeTPEConsumer(AsyncWebsocketConsumer):
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


