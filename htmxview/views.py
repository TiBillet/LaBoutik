import logging
from datetime import timedelta, datetime
from uuid import UUID

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpRequest
from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from epsonprinter.tasks import ticketZ_tasks_printer

from APIcashless.models import ArticleVendu, MoyenPaiement, Configuration, ClotureCaisse
from administration.ticketZ import TicketZ, dround
from htmxview.validators import CashfloatChangeValidator
from webview.serializers import debut_fin_journee
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class Sales(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def list(self, request: Request):

        # ex : wv/allOrders?oldest_first=True
        order = '-date_time'
        authorized_management_mode = False

        oldest_first = False
        if request.GET.get('oldest_first'):
            if request.GET.get('oldest_first').lower().capitalize() == 'True':
                oldest_first = True

        if request.GET.get('authorized_management_mode') is not None:
            if request.GET.get('authorized_management_mode').lower().capitalize() == 'True':
                authorized_management_mode = True

        if oldest_first:
            order = 'date_time,'

        debut_journee, fin_journee = debut_fin_journee()
        # Ex objet :
        # commands_today = CommandeSauvegarde.objects.filter(
        #     archive=False,
        #     datetime__gte=debut_journee
        # ).order_by(order).distinct()

        commands_today = {}
        articles_vendus = ArticleVendu.objects.filter(
            date_time__gte=debut_journee
        ).order_by(order).distinct()

        paginator = Paginator(articles_vendus, 20)
        page_number = request.GET.get('page')

        # Création du dict à envoyer au template
        for article in articles_vendus:
            if commands_today.get(article.commande) == None:
                commands_today[article.commande] = {
                    'articles': [article],
                    'total': article.qty * article.prix,
                    'qty': article.qty,
                }
            else:
                commands_today[article.commande]['articles'].append(article)
                commands_today[article.commande]['total'] += (article.qty * article.prix)
                commands_today[article.commande]['qty'] += article.qty


        # import ipdb; ipdb.set_trace()

        context = {
            'commands_today': commands_today,
            'moyens_paiement': MoyenPaiement.objects.filter(
                categorie__in=[MoyenPaiement.CASH, MoyenPaiement.CHEQUE, MoyenPaiement.CREDIT_CARD_NOFED]),
        }

        return render(request, "sales/sales_list.html", context)

    @action(detail=False, methods=['GET'])
    def z_ticket(self, request):
        # Ticket Z temporaire :
        config = Configuration.get_solo()
        heure_cloture = config.cloture_de_caisse_auto

        start = timezone.localtime()
        if start.time() < heure_cloture:
            # Alors on est au petit matin, on prend la date de la veille
            start = start - timedelta(days=1)
        matin = timezone.make_aware(datetime.combine(start, heure_cloture))
        print('-> url = z_ticket !')

        ticketZ = TicketZ(start_date=matin, end_date=timezone.localtime())
        ticket_today = ticketZ.to_dict if ticketZ.calcul_valeurs() else {}
        context = {
            'ticket_today': ticket_today,
        }
        return render(request, "sales/z_ticket.html", context)

    @action(detail=False, methods=['POST'])
    def change_payment_method(self, request):
        print('-> url = change_payment_method !')

        uuid_command = request.data['uuid_command']
        moyen_paiement = request.data['method_payment_' + uuid_command]
        mp = MoyenPaiement.objects.get(pk=moyen_paiement)

        # change le mode de paiement, si c'est espèce, cheque ou cb
        ArticleVendu.objects.filter(
            commande=uuid_command,
            moyen_paiement__categorie__in=[MoyenPaiement.CASH, MoyenPaiement.CHEQUE, MoyenPaiement.CREDIT_CARD_NOFED]
        ).update(moyen_paiement=mp)

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
                commands_today[article.commande]['total'] = commands_today[article.commande]['total'] + (
                            article.qty * article.prix)

        context = {
            'cmd': commands_today[UUID(uuid_command)],
            'uuid_command': uuid_command,
            'moyens_paiement': MoyenPaiement.objects.filter(
                categorie__in=[MoyenPaiement.CASH, MoyenPaiement.CHEQUE, MoyenPaiement.CREDIT_CARD_NOFED]),
        }

        return render(request, "sales/sales_detail.html", context)


    @action(detail=False, methods=['POST'])
    def change_cash_float(self, request):
        logger.info(request.data)
        validator = CashfloatChangeValidator(data=request.data)
        if not validator.is_valid():
            for error in validator.errors:
                messages.error(request, error)
            return self.z_ticket(request)
        config = Configuration.get_solo()
        config.cash_float = dround(validator.validated_data['cashfloat'])
        config.save()

        return self.z_ticket(request)

    @action(detail=False, methods=['GET'])
    def test_messages(self, request):
        messages.error(request, _("error"))
        # messages.success(request, _("success"))
        # messages.warning(request, _("warning"))
        return self.z_ticket(request)

    @action(detail=False, methods=['GET'])
    def close_all_pos(self, request):

        now = timezone.localtime()
        derniere_fermeture = ClotureCaisse.objects.all().order_by('-end').first()
        if not derniere_fermeture:
            # Aucune cloture de caisse.
            # On charge la datetime du matin :
            config = Configuration.get_solo()
            date_derniere_fermeture = datetime.combine(timezone.localdate(), config.cloture_de_caisse_auto,
                                                       tzinfo=timezone.get_current_timezone())
        else:
            date_derniere_fermeture = derniere_fermeture.end

        # On classe par ordre décroissant de temps ( le plus jeune en premier )
        # On prend le dernier, aka le plus vieux
        premiere_vente_apres_derniere_fermeture = ArticleVendu.objects.filter(
            date_time__gte=date_derniere_fermeture).order_by('-date_time').last()

        # import ipdb; ipdb.set_trace()

        # Aucune vente depuis la dernière fermeture,
        # on envoie la fermeture précédente
        if not premiere_vente_apres_derniere_fermeture:
            messages.error(request, _("No sales since last closing."))
            return self.z_ticket(request)

        start_date = premiere_vente_apres_derniere_fermeture.date_time
        end_date = now

        # Génération du ticket Z
        ticketz_validator = TicketZ(start_date=start_date, end_date=end_date)
        if ticketz_validator.calcul_valeurs():
            ticketz_json = ticketz_validator.to_json

            ClotureCaisse.objects.create(
                ticketZ=ticketz_json,
                start=start_date,
                end=end_date,
                categorie=ClotureCaisse.CLOTURE,
            )

            config = Configuration.get_solo()
            to_printer = ticketZ_tasks_printer.delay(ticketz_json)
            if not config.ticketZ_printer:
                messages.success(request, _("Cash registers closed but no printer configured. You can reprint the ticket from the administration interface."))
                return self.z_ticket(request)

            messages.success(request, _("Cash registers closed."))
            return self.z_ticket(request)

        messages.error(request, _("Error when closing cash register. Contact the potato who coded this."))
        return self.z_ticket(request)


class Membership(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def retrieve(self, request: HttpRequest, pk):
        logger.info(pk)
        pass
