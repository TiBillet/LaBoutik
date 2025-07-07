import json, logging, time
import os
from datetime import timedelta, datetime
from uuid import UUID

import stripe
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from APIcashless.models import ArticleVendu, MoyenPaiement, Configuration, ClotureCaisse, CarteMaitresse, \
    ConfigurationStripe, CarteCashless
from APIcashless.models import PointDeVente, Terminal, PaymentsIntent, GroupementCategorie
from administration.ticketZ import TicketZ, dround
from administration.ticketZ_V4 import TicketZ as TicketZV4
from epsonprinter.tasks import ticketZ_tasks_printer, send_print_order_inner_sunmi
from fedow_connect.fedow_api import FedowAPI
from htmxview.validators import CashfloatChangeValidator, RefillWisePoseValidator
from webview.serializers import debut_fin_journee, CarteCashlessSerializer

from htmxview.tasks import poll_payment_intent_status
logger = logging.getLogger(__name__)


class AppSettings(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    # TODO: besoin d'une variable "autorisation_mode_gerant"(responssable edit.mode) fournie par le serveur,
    # pour la présence du bouton "mode gérant" si autorisé ou pas 
    def list(self, request): # le get /
        config = Configuration.get_solo()
        context = {
            "currency_code": config.currency_code,
            "validation_service_ecran": config.validation_service_ecran,
            "remboursement_auto_annulation": config.remboursement_auto_annulation,
            "void_card": config.void_card,
            "cash_float": config.cash_float,
            "timezone" : config.timezone(),
            "language" : config.language(),
        }

        return render(request, "appsettings/nav.html", context)

    @action(detail=False, methods=['GET'])
    def infos(self, request):
        context = {}

        return render(request, "appsettings/infos.html", context)

    @action(detail=False, methods=['GET'])
    def language(self, request):
        config = Configuration.get_solo()
        context = {
            "timezone" : config.timezone(),
            "language" : config.language(),
        }

        return render(request, "appsettings/language.html", context)

    @action(detail=False, methods=['GET'])
    def printer(self, request):
        context = {}

        return render(request, "appsettings/printer.html", context)

    @action(detail=False, methods=['GET'])
    def nfc(self, request):
        context = {}

        return render(request, "appsettings/nfc.html", context)

    @action(detail=False, methods=['GET'])
    def logs(self, request):
        context = {}

        return render(request, "appsettings/logs.html", context)

    # TODO: remplacer la requête si-dessous par un GET; le serveur donnera les 2 valeurs
    # autorisation_mode_gerant(responssable edit.mode) et mode_gerant = activé/désactivé (n'existe pas, a créer).
    @action(detail=False, methods=['POST'])
    def manager_mode(self, request: Request):
        activation_mode_gerant = request.data.get('activation_mode_gerant')
        autorisation_mode_gerant = request.data.get('autorisation_mode_gerant')
        context = {
            "activation_mode_gerant": activation_mode_gerant,
            "autorisation_mode_gerant": autorisation_mode_gerant
        }

        return render(request, "appsettings/manager_mode.html", context)


class Sales(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def list(self, request):
        context = {}
        return render(request, "sales/sales.html", context)

    @action(detail=False, methods=['POST'])
    def sales_list(self, request: Request):
        # ex : wv/allOrders?oldest_first=True
        order = '-date_time'
        authorized_management_mode = False

        tagid_carte_primaire = request.data.get('tagIdCm')
        logger.info(f"tagid_carte_primaire = {tagid_carte_primaire}")
        carte_primaire = CarteMaitresse.objects.get(carte__tag_id=tagid_carte_primaire)
        points_de_vente = carte_primaire.points_de_vente.all()

        logger.info(f"points_de_vente = {points_de_vente}")


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
            date_time__gte=debut_journee,
            pos__in=points_de_vente,
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


    @action(detail=False, methods=['POST'])
    def z_ticket(self, request):
        tagid_carte_primaire = request.data.get('tagIdCm')
        logger.info(f"tagid_carte_primaire = {tagid_carte_primaire}")
        carte_primaire = CarteMaitresse.objects.get(carte__tag_id=tagid_carte_primaire)
        points_de_vente = carte_primaire.points_de_vente.all()

        logger.info(f"points_de_vente = {points_de_vente}")

        config = Configuration.get_solo()
        heure_cloture = config.cloture_de_caisse_auto

        start = timezone.localtime()
        if start.time() < heure_cloture:
            # Alors on est au petit matin, on prend la date de la veille
            start = start - timedelta(days=1)
        matin = timezone.make_aware(datetime.combine(start, heure_cloture))

        ticketZ = TicketZV4(start_date=matin, end_date=timezone.localtime(), points_de_vente=points_de_vente)
        # Le context json lance le calcul et s'assure qu'il est serialisable.
        json_context = ticketZ.json_context()
        context = json.loads(json_context)
        context['carte_primaire'] = carte_primaire

        # on pourrait envoyer le query_context, mais avec le json.loads on s'assure que le json stoqué en DB est OK
        return render(request, "sales/z_ticket.html", context=context)

    @action(detail=False, methods=['POST'])
    def articles_list(self, request):
        tagid_carte_primaire = request.data.get('tagIdCm')
        logger.info(f"tagid_carte_primaire = {tagid_carte_primaire}")
        carte_primaire = CarteMaitresse.objects.get(carte__tag_id=tagid_carte_primaire)
        points_de_vente = carte_primaire.points_de_vente.all()

        logger.info(f"points_de_vente = {points_de_vente}")

        config = Configuration.get_solo()
        heure_cloture = config.cloture_de_caisse_auto

        start = timezone.localtime()
        if start.time() < heure_cloture:
            # Alors on est au petit matin, on prend la date de la veille
            start = start - timedelta(days=1)
        matin = timezone.make_aware(datetime.combine(start, heure_cloture))

        ticketZ = TicketZV4(start_date=matin, end_date=timezone.localtime(), points_de_vente=points_de_vente)
        # Le context json lance le calcul et s'assure qu'il est serialisable.
        json_context = ticketZ.json_context()
        context = json.loads(json_context)
        context['carte_primaire'] = carte_primaire

        # on pourrait envoyer le query_context, mais avec le json.loads on s'assure que le json stoqué en DB est OK
        return render(request, "sales/articles_list.html", context=context)



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
        ticketZ = TicketZ(start_date=matin, end_date=timezone.localtime())  #TODO : PASSER en TicketV4
        # On calcule les valeurs et on récupère le dictionnaire, sinon un dict vide
        ticket_today = ticketZ.to_dict if ticketZ.calcul_valeurs() else {}
        if ticket_today:
            send_print_order_inner_sunmi.delay(ws_channel=ws_room_appareil, data=ticketZ.to_sunmi_printer_57())

        context = {'ticket_today': ticket_today,}

        return HttpResponse(status=200)


    @action(detail=True, methods=['GET'])
    def print_ticket_purchases_get(self, request, pk):
        uuid_paiement = pk
        articles = ArticleVendu.objects.filter(uuid_paiement=uuid_paiement)

        # Get business information from Configuration
        config = Configuration.get_solo()
        currency = config.currency_code

        printer = None
        if not hasattr(request.user, "appareil"):
            logger.info(f"No appareil found for user {request.user}")
            printer = config.ticketZ_printer
        elif not request.user.appareil.printers.exists():
            logger.info(f"No printer found for appareil {request.user.appareil}")
            printer = config.ticketZ_printer
        else:
            printer = request.user.appareil.printers.first()
            logger.info(f"Found printer for appareil {printer}")

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
                'unit_price': f"{dround(article.prix)} {currency}",
                'total_price': f"{dround(article.prix * article.qty)} {currency}",
                'vat_rate': dround(article.tva),
            } for article in articles],

            # Totals
            'total_ttc': f"{dround(total_ttc)} {currency}",
            'total_ht': f"{dround(total_ht)} {currency}",
            'total_tva': f"{dround(total_tva)} {currency}",

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
    def print_ticket_purchases(self, request):
        print('-> Print ticket purchases !')
        logger.info(f"-----> request.data = {request.data}")
        logger.info(f"-----> request.user = {request.user}")
        uuid_paiement = request.data['uuid_paiement']

        return self.print_ticket_purchases_get(request, uuid_paiement)


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


class Kiosk(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    # La vue GET par default /htmx/kiosk
    def list(self, request):
        context = {
            "test":settings.TEST,
            "DEMO_TAGID_CLIENT1" : os.environ.get('DEMO_TAGID_CLIENT1'),
        }
        return render(request, "kiosk/montant.html", context)

    # menu kiosque
    @action(detail=False, methods=['GET'])
    def request_card(self, request, *args, **kwargs):
        context = {
            "tag_id": None,
        }
        return render(request, 'tpe/request_card.html', context)

    # test tagId carte
    @action(detail=False, methods=['POST'])
    def check_request_card(self, request, *args, **kwargs):
        tag_id = request.data['tag_id']
        logger.info(f"--> tag_id = {tag_id}")

        fedowApi = FedowAPI()
        fedowApi.NFCcard.retrieve(tag_id)
        carte = CarteCashless.objects.get(tag_id=tag_id)

        user = request.user

        # TODO : lier le terminal à l'appareil / user
        terminal = Terminal.objects.filter(type=Terminal.STRIPE_WISEPOS, archived=False).first()
        context = {
            "total_monnaie": carte.total_monnaie(),
            "card": carte,
            'terminal': terminal,
            'user' : user,
        }
        return render(request, "kiosk/montant.html", context)


    @action(detail=False, methods=['POST'])
    def refill_with_wisepos(self, request, *args, **kwargs):
        user = request.user

        # import ipdb; ipdb.set_trace()

        if not settings.DEBUG:
            if not request.user.is_authenticated or not hasattr(request.user, 'appareil'):
                logger.error(f"ERROR NOT AUTHENTICATED OR NOT APPAREIL")
                raise Exception(f"ERROR NOT AUTHENTICATED OR NOT APPAREIL")

        # Validate the request data
        logger.info(f"request.data = {request.data}")
        validator = RefillWisePoseValidator(data=request.data)
        if not validator.is_valid():
            logger.error(f"ERROR VALIDATION : {validator.errors}")
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get validated data
        validated_data = validator.validated_data
        amount = validated_data['totalAmount']
        terminal = user.appareil.terminals.filter(type=Terminal.STRIPE_WISEPOS, archived=False).first()
        carte = validator.card

        kiosk = PointDeVente.objects.get(comportement=PointDeVente.KIOSK)

        # Création de l'intention de paiement
        payment_intent = PaymentsIntent.objects.create(
            terminal=terminal,
            amount=amount,
            pos=kiosk,
            card=carte,
        )

        # Envoi de l'intention de paiement au terminal
        try :
            payment_intent = payment_intent.send_to_terminal(terminal)
        except Exception as e:
            context = {
                "total_monnaie": carte.total_monnaie(),
                "card": carte,
                'terminal': terminal,
                'user': user,
                'error_message': f"{e}",
            }
            return render(request, "kiosk/montant.html", context)


        # Lancer la tâche Celery pour surveiller le statut du paiement
        logger.info(f"\nStarted Celery task to poll payment intent status for ID: {payment_intent.pk}")
        poll_payment = poll_payment_intent_status.delay(payment_intent.pk)

        # Check que la requete celery est bien ok
        retry_count = 0
        while poll_payment.status != "STARTED" :
            logger.info(f"WAIT POLLING PAYMENT INTENT STATUS {poll_payment.status} RESULT : {poll_payment.result}")
            time.sleep(1)
            retry_count += 1
            if retry_count > 5:
                break

        if poll_payment.status != 'STARTED':
            logger.error(f"WAIT POLLING PAYMENT INTENT STATUS {poll_payment.status} RESULT : {poll_payment.result}")
            return Response(poll_payment.result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"END WAIT POLLING PAYMENT INTENT STATUS {poll_payment.status} RESULT : {poll_payment.result}")

        # Renvoie la partie websocket pour le suivi de l'intention de paiement
        return render(request, 'kiosk/confirmationCB.html', context={
            'user': user,
            'terminal': terminal,
            'payment_intent': payment_intent,
        })


    @action(detail=True, methods=['GET'])
    def retry(self, request, pk):
        config_stripe = ConfigurationStripe.get_solo()
        stripe.api_key = config_stripe.get_stripe_api()
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
        config_stripe = ConfigurationStripe.get_solo()
        stripe.api_key = config_stripe.get_stripe_api()
        terminal = get_object_or_404(Terminal, pk=pk)
        stripe.terminal.Reader.cancel_action(terminal.stripe_id)
        return HttpResponse(status=205)

    @action(detail=True, methods=['GET'])
    def valid_and_continue(self, request, pk):
        config_stripe = ConfigurationStripe.get_solo()
        stripe.api_key = config_stripe.get_stripe_api()

        # Get the payment intent
        payment_intent = get_object_or_404(PaymentsIntent, pk=pk)
        terminal = payment_intent.terminal
        status = payment_intent.get_from_stripe()
        logger.info(f"Status = {status}")

        try:
            if status == PaymentsIntent.REQUIRES_PAYMENT_METHOD:
                message = "En attente de paiement."
            elif status == PaymentsIntent.REQUIRES_CAPTURE:
                message = "Paiement validé."
            elif status == PaymentsIntent.SUCCEEDED:
                message = 'Paiement déjà validé!'
            elif status == PaymentsIntent.IN_PROGRESS:
                message= 'Paiement en cours de traitement. Veuillez attendre.'
            else:
                raise ValueError(f"Unknown status: {payment_intent.get_status_display()}")
            return render(request, 'tpe/create.html', context={
                'user': request.user,
                'terminal': terminal,
                'payment_intent': payment_intent,
                'message': message
            })

        except Exception as e:
            logger.error(f"Error processing payment: {e}")

            # Return to the create template with error message
            return render(request, 'tpe/create.html', context={
                'user': request.user,
                'terminal': terminal,
                'payment_intent': payment_intent,
                'error': f"Erreur lors du traitement du paiement: {str(e)}"
            })

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
