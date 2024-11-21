import logging

from django.http import HttpRequest
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from APIcashless.models import CommandeSauvegarde, CarteCashless, CarteMaitresse, ArticleVendu
from administration.adminroot import ArticlesAdmin
from webview.serializers import debut_fin_journee, CommandeSerializer

logger = logging.getLogger(__name__)


class Sales(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def list(self, request: Request):

        # ex : wv/allOrders?oldest_first=True
        order = '-datetime'
        authorized_management_mode = False

        oldest_first = False
        if request.GET.get('oldest_first'):
            if request.GET.get('oldest_first').lower().capitalize() == 'True':
                oldest_first = True

        if request.GET.get('authorized_management_mode') is not None:
            if request.GET.get('authorized_management_mode').lower().capitalize() == 'True':
                authorized_management_mode = True

        print(f'oldest_first = {oldest_first}')
        print(f'authorized_management_mode = {authorized_management_mode}')

        if oldest_first:
            order = 'datetime'

        debut_journee, fin_journee = debut_fin_journee()
        # Ex objet :
        # commands_today = CommandeSauvegarde.objects.filter(
        #     archive=False,
        #     datetime__gte=debut_journee
        # ).order_by(order).distinct()

        commands_today = {}
        articles_vendus = ArticleVendu.objects.filter(
            date_time__gte=debut_journee
        )
        for article in articles_vendus:
            if commands_today.get(article.commande) :
                commands_today[article.commande] += article
            else:
                commands_today[article.commande] = article

        context = {
            'commands_today': commands_today,
            'authorized_management_mode': authorized_management_mode,
            'oldest_first': oldest_first,
            }

        return render(request, "sales/list.html", context)

    #logger.info(f'data = { cmd.items() }')
    #import ipdb; ipdb.set_trace()
    def create(self, request: HttpRequest):
        # TODO: sécuriser la méthode, try catch ?

        data = request.data
        print(f"data: {data}")
        tag_id_cm = data['tag_id_cm']

        # récupère carte
        carte = CarteCashless.objects.filter(tag_id=tag_id_cm)[0]
        authorized_management_mode = CarteMaitresse.objects.get(carte_id=carte.id).edit_mode

        # TODO: back => valider la commande
        # dev mock, à remplacer par la validatio de la commande
        validateOrder = True

        # commande validée
        order = CommandeSauvegarde.objects.filter(uuid=data['uuid_commande'])
        print(f"order: {order.values()}")

        context = { 
            'authorized_management_mode': authorized_management_mode,
            'validateOrder': validateOrder,
            'cmd': order[0]
        }

        # retour partiel htmx
        return render(request, "sales/components/order.html", context)


class Membership(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def retrieve(self, request: HttpRequest, pk):
        logger.info(pk)
        pass
