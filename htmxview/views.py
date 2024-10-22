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
        oldest_first = request.GET.get('oldest_first')
        if oldest_first:
            order = 'datetime'

        debut_journee, fin_journee = debut_fin_journee()
        commands_today = CommandeSauvegarde.objects.filter(
            archive=False,
            datetime__gte=debut_journee
        ).order_by(order).distinct()

        all_order = CommandeSerializer(instance=commands_today, many=True)
        logger.info(f'all_order. = {all_order.data}')

        return render(request, "sales/list.html")
