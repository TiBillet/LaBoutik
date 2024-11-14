import logging

from django.http import HttpRequest
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from APIcashless.models import CommandeSauvegarde, CarteCashless, CarteMaitresse
from webview.serializers import debut_fin_journee, CommandeSerializer

logger = logging.getLogger(__name__)


class Sales(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def list(self, request: HttpRequest):

        # ex : wv/allOrders?oldest_first=True
        order = '-datetime'
        oldest_first = True if request.GET.get('oldest_first').lower().capitalize() == 'True' else False
        mode_manage = True if request.GET.get('mode_manage').lower().capitalize() == 'True' else False

        if oldest_first:
            order = 'datetime'

        debut_journee, fin_journee = debut_fin_journee()
        commands_today = CommandeSauvegarde.objects.filter(
            archive=False,
            datetime__gte=debut_journee
        ).order_by(order).distinct()

        context = {
            'commands_today': commands_today,
            'mode_manage': mode_manage,
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
        managementMode = CarteMaitresse.objects.get(carte_id=carte.id).edit_mode

        # TODO: back => valider la commande
        # dev mock, à remplacer par la validatio de la commande
        validateOrder = True

        # commande validée
        order = CommandeSauvegarde.objects.filter(uuid=data['uuid_commande'])
        print(f"order: {order.values()}")

        context = { 
            'managementMode': managementMode,
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
