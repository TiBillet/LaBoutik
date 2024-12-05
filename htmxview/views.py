import logging
from datetime import timedelta, datetime
from lib2to3.fixes.fix_input import context

from django.http import HttpRequest
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from APIcashless.models import CommandeSauvegarde, CarteCashless, CarteMaitresse, ArticleVendu, MoyenPaiement, \
    Configuration, PointDeVente
from administration.adminroot import ArticlesAdmin
from administration.ticketZ import TicketZ
from webview.serializers import debut_fin_journee, CommandeSerializer
from django.core.paginator import Paginator
# nico
from uuid import UUID

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

        paginator = Paginator(articles_vendus, 20)
        page_number = request.GET.get('page')

        for article in articles_vendus:
            if commands_today.get(article.commande) == None:
                commands_today[article.commande] = {
                    'articles': [article],
                    'total': article.qty * article.prix
                }
            else:
                commands_today[article.commande]['articles'].append(article)
                commands_today[article.commande]['total'] = commands_today[article.commande]['total'] + (article.qty * article.prix)

        # Ticket Z temporaire :
        config = Configuration.get_solo()
        heure_cloture = config.cloture_de_caisse_auto

        start = timezone.localtime()
        if start.time() < heure_cloture:
            # Alors on est au petit matin, on prend la date de la veille
            start = start - timedelta(days=1)
        matin = timezone.make_aware(datetime.combine(start, heure_cloture))

        ticketZ = TicketZ(start_date=matin, end_date=timezone.localtime())
        ticket_today = ticketZ.to_dict if ticketZ.calcul_valeurs() else {}

        context = {
            'ticket_today': ticket_today,
            'commands_today': commands_today,
            'moyens_paiement': MoyenPaiement.objects.filter(categorie__in=[MoyenPaiement.CASH,MoyenPaiement.CHEQUE,MoyenPaiement.CREDIT_CARD_NOFED]),
            }

        return render(request, "sales/list.html", context)

    @action(detail=False, methods=['POST'])
    def change_payment_method(self, request):
        print('-> url = change_payment_method !')

        uuid_command = request.data['uuid_command']
        moyen_paiement = request.data['method_payment_' + uuid_command]
        mp = MoyenPaiement.objects.get(pk=moyen_paiement)

        # change le mode de paiement
        ArticleVendu.objects.filter(commande=uuid_command).update(moyen_paiement=mp)

        commands_today = {}
        # get articles from uuid command
        articles_vendus = ArticleVendu.objects.filter(commande=uuid_command)
        print(f"articles_vendus = {articles_vendus}")

        for article in articles_vendus:
            if commands_today.get(article.commande) == None:
                commands_today[article.commande] = {
                    'articles': [article],
                    'total': article.qty * article.prix
                }
            else:
                commands_today[article.commande]['articles'].append(article)
                commands_today[article.commande]['total'] = commands_today[article.commande]['total'] + (article.qty * article.prix)

        # import ipdb; ipdb.set_trace()
        context = {
            'cmd': commands_today[UUID(uuid_command)],
            'uuid_command': uuid_command,
            'moyens_paiement': MoyenPaiement.objects.filter(categorie__in=[MoyenPaiement.CASH,MoyenPaiement.CHEQUE,MoyenPaiement.CREDIT_CARD_NOFED]),
        }

        return render(request, "sales/components/order.html", context)

class Membership(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def retrieve(self, request: HttpRequest, pk):
        logger.info(pk)
        pass


class TpeStripe(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    @action(detail=False, methods=['GET'])
    def index(self, request, *args, **kwargs):
        user = request.user
        context={'user':user}
        return render(request, 'websocket/tpe_stripe/index.html', context)




### TUTORIEL WEBSOCKET

def tuto_htmx(request):
    # if settings.DEBUG:
    #     pos = PointDeVente.objects.all().order_by('poid_liste').first()
    # else :
    pos = PointDeVente.objects.first()

    context = {'pos': pos}
    return render(request, 'websocket/tuto_htmx/index.html', context)


def tuto_js(request, room_name):
    return render(request, 'websocket/tuto_js/room.html', {'room_name': room_name})
