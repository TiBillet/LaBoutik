from django.shortcuts import render

from laboutik_core.models import Product


# Create your views here.


def products(request):
    products = Product.objects.all()
    return render(request, 'products.html', {'products': products})