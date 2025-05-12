import logging
from datetime import timedelta, datetime
# nico
from uuid import UUID

import stripe
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from APIcashless.models import ArticleVendu, MoyenPaiement, Configuration, ClotureCaisse
from APIcashless.models import PointDeVente, Terminal, PaymentsIntent, GroupementCategorie
from administration.ticketZ import TicketZ, dround
from epsonprinter.tasks import ticketZ_tasks_printer, send_print_order_inner_sunmi
from htmxview.validators import CashfloatChangeValidator
from webview.serializers import debut_fin_journee

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


    @action(detail=False, methods=['GET'])
    def print_temp_ticket(self, request):
        # Ticket Z temporaire :
        user = request.user
        # Le wscanal est celui de l'appareil
        ws_room_appareil = user.uuid.hex
        # On récupère la configuration de la DB
        config = Configuration.get_solo()
        # On récupère l'heure de clôture de caisse configurée
        heure_cloture = config.cloture_de_caisse_auto

        # On récupère la date/heure locale actuelle
        start = timezone.localtime()
        if start.time() < heure_cloture:
            # Si on est avant l'heure de clôture, on est au petit matin
            # donc on doit prendre la date de la veille
            start = start - timedelta(days=1)
        # On crée une date/heure avec la date du start et l'heure de clôture
        matin = timezone.make_aware(datetime.combine(start, heure_cloture))
        print('-> url = z_ticket !')

        # On crée le ticket Z entre le matin et maintenant
        ticketZ = TicketZ(start_date=matin, end_date=timezone.localtime())
        # On calcule les valeurs et on récupère le dictionnaire, sinon un dict vide
        ticket_today = ticketZ.to_dict if ticketZ.calcul_valeurs() else {}
        if ticket_today:
            send_print_order_inner_sunmi.delay(ws_channel=ws_room_appareil, data=ticketZ.to_sunmi_printer_57())

        context = {'ticket_today': ticket_today,}
        return render(request, "sales/z_ticket.html", context)

    @action(detail=False, methods=['POST'])
    def print_ticket_purchases(self, request):
        print('-> Print ticket purchases !')
        logger.info(f"-----> request.data = {request.data}")
        uuid_paiement = request.data['uuid_paiement']
        articles = ArticleVendu.objects.filter(uuid_paiement=uuid_paiement)

        # Get business information from Configuration
        config = Configuration.get_solo()

        printer = None
        if not hasattr(request.user, "appareil"):
            printer = config.ticketZ_printer
        elif not hasattr(request.user.appreil, 'printer'):
            printer = config.ticketZ_printer
        else:
            printer = request.user.appareil.printer

        if not printer:
            context = {'message': _("No printer configured for this terminal.")}
            return render(request, "sales/sales_print_ticket_purchases_status.html", context)


        if not articles.exists():
            logger.error(f"No articles found for uuid_paiement: {uuid_paiement}")
            context = {'error': 'No articles found'}
            return render(request, "sales/sales_print_ticket_purchases_status.html", context)



        # Get the first article to extract common information
        first_article = articles.first()

        # Calculate totals
        total_ttc = sum(article.prix * article.qty for article in articles)
        total_ht = sum(article.ht_from_ttc() * article.qty for article in articles)
        total_tva = total_ttc - total_ht

        # Create the ticket data dictionary
        ticket_data = {
            'printer_id': str(printer.id),
            # Business information
            'business_name': config.structure,
            'business_address': config.adresse,
            'business_siret': config.siret,
            'business_vat_number': config.numero_tva,
            'business_phone': config.telephone,
            'business_email': config.email,

            # Receipt information
            'date_time': first_article.date_time.astimezone().strftime('%d/%m/%Y %H:%M'),
            'receipt_id': str(uuid_paiement)[:8],
            'table': first_article.table.name if first_article.table else '',
            'server': first_article.responsable.name if first_article.responsable else '',

            # Articles information
            'articles': [{
                'name': article.article.name,
                'quantity': dround(article.qty),
                'unit_price': dround(article.prix),
                'total_price': dround(article.prix * article.qty),
                'vat_rate': dround(article.tva),
            } for article in articles],

            # Totals
            'total_ttc': dround(total_ttc),
            'total_ht': dround(total_ht),
            'total_tva': dround(total_tva),

            # Payment information
            'payment_method': first_article.moyen_paiement.name if first_article.moyen_paiement else '',

            # Footer
            'footer': config.pied_ticket,
        }

        # Import here to avoid circular imports
        from epsonprinter.tasks import print_ticket_purchases_task

        # Send the ticket to the printer
        print_ticket_purchases_task.delay(ticket_data)

        context = {'success': True}
        return render(request, "sales/sales_print_ticket_purchases_status.html", context)

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


class Print(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    @action(detail=False, methods=['GET'])
    def test(self, request, *args, **kwargs):
        # On se log sur le premier appareil pour entrer dans le websocket
        User = get_user_model()
        user = User.objects.filter(appareil__isnull=False).first()

        return render(request, 'print/test.html', context={
            'user': user,
            'room_name': user.uuid.hex,
            'grps': GroupementCategorie.objects.all(),
        })

    @action(detail=True, methods=['GET'])
    def test_groupe(self, request, pk, *args, **kwargs):
        groupe = GroupementCategorie.objects.get(pk=pk)
        user = request.user

        try :
            destination = groupe.printer.host.user.uuid.hex

            # On envoi sur le canal que seul l'appareil reçoit l'ordre d'impression depuis le WS
            logger.info(f"HTTP Print/test_groupe : tentative d'envoi de message vers WS sur le canal {destination}")
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                destination,
                {
                    'type': f'from_ws_to_printer',
                    'text': 'Print me !'
                }
            )

        except Exception as e:
            logger.error(f"Pas d'appareil pour ce groupe ? -> {e}")
            pass

        return render(request, 'print/notification.html', context={
            'user': user,
            'room_name': request.user.uuid.hex,
            'groupe': groupe,
        })


class PaymentIntentTpeViewset(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def check_reader_state(self, reader):
        pass

    def create(self, request, *args, **kwargs):
        user = request.user
        amount = request.data['amount']

        if not settings.DEBUG:
            if not request.user.is_authenticated or not hasattr(request.user, 'appareil'):
                logger.error(f"ERROR NOT AUTHENTICATED OR NOT APPAREIL")
                raise Exception(f"ERROR NOT AUTHENTICATED OR NOT APPAREIL")

        # Lier le tpe a l'appareil/user
        terminal = Terminal.objects.first()

        payment_intent = PaymentsIntent.objects.create(
            terminal=terminal,
            amount=amount,
        )
        payment_intent.send_to_terminal(terminal)

        return render(request, 'tpe/create.html', context={
            'user': user,
            'terminal': terminal,
            'payment_intent': payment_intent,
        })

    @action(detail=True, methods=['GET'])
    def retry(self, request, pk):
        payment_intent = get_object_or_404(PaymentsIntent, pk=pk)
        terminal = payment_intent.terminal
        stripe.terminal.Reader.cancel_action(terminal.stripe_id)
        payment_intent.send_to_terminal(terminal)

        return render(request, 'tpe/create.html', context={
            'user': request.user,
            'terminal': terminal,
            'payment_intent': payment_intent,
        })

    @action(detail=True, methods=['GET'])
    def cancel(self, request, pk):
        config = Configuration.get_solo()
        stripe.api_key = config.get_stripe_api()
        terminal = get_object_or_404(Terminal, pk=pk)
        stripe.terminal.Reader.cancel_action(terminal.stripe_id)
        return HttpResponse(status=205)


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
