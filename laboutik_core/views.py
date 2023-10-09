from django.http import HttpResponseRedirect
from django.shortcuts import render
from rest_framework import viewsets

from laboutik_core.models import Product


class ProductAPI(viewsets.ViewSet):
    """
    API :
    Lister les produits : GET /api/products/
    Detail d'un produit : GET /api/products/<pk>
    Création d'un produit : POST /api/products/
    """

    def list(self, request):
        "Controleur pour GET"
        products = Product.objects.all()
        return render(request, 'products.html', {'products': products})

    def retrieve(self, request, pk=None):
        "Controleur pour GET api/products/<pk>"
        product = Product.objects.get(pk=pk)
        if request.query_params.get('edit') == 'true':
            return render(request, 'tableau_produit/ligne_edition_produit.html', {'product': product})

        return render(request, 'tableau_produit/ligne_produit.html', {'product': product})

    def create(self, request):
        "Controleur pour POST"
        data = request.data
        Product.objects.create(name=data.get('name'))

        return HttpResponseRedirect('/api/products/')

    def update(self, request, pk=None):
        "Controleur pour PUT"
        data = request.data
        product = Product.objects.get(pk=pk)
        product.name = data.get('name_updated')
        product.save()

        return render(request, 'tableau_produit/ligne_produit.html', {'product': product})

    def destroy(self, request, pk=None):
        "Controleur pour DELETE"
        product = Product.objects.get(pk=pk)
        product.delete()

        return HttpResponseRedirect('/api/products/')

        # Product.objects.create()
