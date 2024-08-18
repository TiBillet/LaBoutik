from django.urls import path, include
from kiosk.views import (index, CardViewset, DeviceViewset,
                stripe_paiment, press_to_start_page)
from rest_framework import routers
router = routers.DefaultRouter()

router.register(r'card', CardViewset, basename='card')
router.register(r'device', DeviceViewset, basename='device')

urlpatterns = [
    path('index/', index, name='index'),
    path('press_start/', press_to_start_page, name='press_start'),
    path('api/', include(router.urls)),

    path('stripe_paiment/', stripe_paiment, name='stripe_paiment'),
    path('', index, name='index'),
]
