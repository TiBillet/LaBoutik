import logging

from django.http import HttpRequest
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from APIcashless.models import CommandeSauvegarde
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

        # all_order = CommandeSerializer(instance=commands_today, many=True)
        #logger.info(f'data = { cmd.items() }')
        context = {
            'commands_today': commands_today,
            'mode_manage': mode_manage,
            'oldest_first': oldest_first
            }

        # import ipdb; ipdb.set_trace()
        return render(request, "sales/list.html", context)


    def create(self, request: HttpRequest):
        data = request.data
        print(f"Creating new MyModel with data: {data}")
        context = { 'title': 'salut'}
        # TODO: back à valider
        # retour partiel htmx
        return render(request, "sales/test.html", context)


class Membership(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def retrieve(self, request: HttpRequest, pk):
        logger.info(pk)
        pass