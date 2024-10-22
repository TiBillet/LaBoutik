

from django.conf.urls import url
from django.urls import path, include

from webview import views


from rest_framework import routers

from htmxview import views

router = routers.DefaultRouter()

router.register(r'sales', views.Sales, basename='sales')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [] + router.urls