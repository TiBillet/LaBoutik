# Cashless/asgi.py
import django
import os
import webview.routing
from channels.http import AsgiHandler

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django.setup()

application = ProtocolTypeRouter({
    "http": AsgiHandler(),
    # AllowedHost vérifie le ALLOWED_HOST de settings
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                webview.routing.websocket_urlpatterns
            )
        ),
    ),
})
