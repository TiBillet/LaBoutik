# chat/routing.py
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # TPE STRIPE
    re_path(r'ws/terminal/(?P<room_name>\w+)/$', consumers.TerminalConsumer.as_asgi()),

    # Pour les tutoriels :
    re_path(r'ws/tuto_js/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/tuto_htmx/(?P<room_name>\w+)/$', consumers.HtmxConsumer.as_asgi()),
]