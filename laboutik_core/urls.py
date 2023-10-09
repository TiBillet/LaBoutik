from django.urls import path, include
from rest_framework import routers

from . import views
from django.conf import settings
from django.conf.urls.static import static

from .views import ProductAPI

router = routers.DefaultRouter()

router.register('products', ProductAPI, basename="product_api")
# router.register('price', PriceAPI, basename="price_api")

urlpatterns = [
        path('api/', include(router.urls)),
]