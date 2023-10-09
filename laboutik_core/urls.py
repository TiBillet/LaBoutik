from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

from .views import products

urlpatterns = [
        path('products/', products, name='products'),
]