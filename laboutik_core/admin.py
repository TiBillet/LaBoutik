from django.contrib import admin
from laboutik_core.models import Category, Product, Price
# Créer superuser : ./manage.py createsuperuser


admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Price)
