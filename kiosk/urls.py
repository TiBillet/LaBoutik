from django.urls import path, include
from kiosk.views import (index, CardViewset, DeviceViewset,
                stripe_paiment)
from rest_framework import routers
router = routers.DefaultRouter()

router.register(r'card', CardViewset, basename='card')
router.register(r'device', DeviceViewset, basename='device')

urlpatterns = [
    path('index/', index, name='index'),
    path('api/', include(router.urls)),
    # path('recharge_paiment_pg/', recharge_paiment_pg, name='recharge_paiment_pg'),
    # path('given_bill/', given_bill, name='given_bill'),
    # path('recharge/', recharge, name='recharge'),
    path('stripe_paiment/', stripe_paiment, name='stripe_paiment'),
    path('', index, name='index'),
]
