import decimal
import json
import logging
from datetime import timedelta, datetime

import dateutil.parser
import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.signing import TimestampSigner, SignatureExpired
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode
from django_weasyprint import WeasyTemplateView
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import ugettext_lazy as _

from APIcashless.models import RapportTableauComptable, Configuration, ArticleVendu, ClotureCaisse, Articles, \
    Appareil
from APIcashless.tasks import envoie_rapport_et_ticketz_par_mail, GetOrCreateRapportFromDate, email_new_hardware
from administration.ticketZ import TicketZ
from administration.ticketZ_V4 import TicketZ as TicketZV4

from epsonprinter.tasks import ticketZ_tasks_printer

logger = logging.getLogger(__name__)


# Create your views here.


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


#
# def start_end_event_4h_am(date, fuseau_horaire=None, heure_pivot=4):
#     if fuseau_horaire is None:
#         config = Configuration.get_solo()
#         fuseau_horaire = config.fuseau_horaire
#
#     tzlocal = pytz.timezone(fuseau_horaire)
#     debut_event = tzlocal.localize(datetime.combine(date, datetime.min.time()), is_dst=None) + timedelta(
#         hours=heure_pivot)
#     fin_event = tzlocal.localize(datetime.combine(date, datetime.min.time()), is_dst=None) + timedelta(
#         days=1, hours=heure_pivot)
#     return debut_event, fin_event


### NEW METHOD CLOTURE CAISSE
class TicketZToday(APIView):
    template_name = "rapports/V4.html"
    permission_classes = [IsAuthenticated]

    def get(self, request):
        config = Configuration.get_solo()
        heure_cloture = config.cloture_de_caisse_auto

        start = timezone.localtime()
        if start.time() < heure_cloture:
            # Alors on est au petit matin, on prend la date de la veille
            start = start - timedelta(days=1)
        matin = timezone.make_aware(datetime.combine(start, heure_cloture))

        ticketZ = TicketZV4(start_date=matin, end_date=timezone.localtime())
        return render(request, self.template_name, context=ticketZ.context())
        # return HttpResponse('No sales today')


class RapportToday(APIView):
    template_name = "rapports/rapport_complet.html"
    permission_classes = [IsAuthenticated]

    def get(self, request):
        config = Configuration.get_solo()
        heure_cloture = config.cloture_de_caisse_auto

        start = timezone.localtime()
        if start.time() < heure_cloture:
            # Alors on est au petit matin, on prend la date de la veille
            start = start - timedelta(days=1)
        matin = timezone.make_aware(datetime.combine(start, heure_cloture))

        ticketZ = TicketZ(start_date=matin, end_date=timezone.localtime())
        if ticketZ.calcul_valeurs():
            return render(request, self.template_name, context=ticketZ.to_dict)
        return HttpResponse('No sales today')


class TicketZsimpleFromCloture(APIView):
    template_name = "rapports/ticketZ_simple.html"
    permission_classes = [IsAuthenticated]

    def get(self, request, pk_uuid):
        cloture_caisse = get_object_or_404(ClotureCaisse, pk=pk_uuid)
        ticket_z = json.loads(cloture_caisse.ticketZ)
        ticket_z['start_date'] = dateutil.parser.parse(ticket_z['start_date'])
        ticket_z['end_date'] = dateutil.parser.parse(ticket_z['end_date'])
        # import ipdb; ipdb.set_trace()
        return render(request, self.template_name, context=ticket_z)


class RapportFromCloture(APIView):
    template_name = "rapports/rapport_complet.html"
    permission_classes = [IsAuthenticated]

    def get(self, request, pk_uuid):
        cloture_caisse = get_object_or_404(ClotureCaisse, pk=pk_uuid)
        ticket_z = json.loads(cloture_caisse.ticketZ)
        ticket_z['start_date'] = dateutil.parser.parse(ticket_z['start_date'])
        ticket_z['end_date'] = dateutil.parser.parse(ticket_z['end_date'])
        return render(request, self.template_name, context=ticket_z)


class ClotureToMail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk_uuid):
        cloture_caisse = get_object_or_404(ClotureCaisse, pk=pk_uuid)
        config = Configuration.get_solo()
        email = config.compta_email if config.compta_email else config.email
        envoie_rapport_et_ticketz_par_mail.delay(cloture_caisse.pk)
        messages.add_message(request, messages.SUCCESS,
                             f"Génération en cours pour {cloture_caisse.start} - {cloture_caisse.end}. Les rapports seront envoyés sur {email}")
        return HttpResponseRedirect(request.query_params.get('next'))


class ClotureToPrinter(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk_uuid):
        cloture_caisse = get_object_or_404(ClotureCaisse, pk=pk_uuid)
        config = Configuration.get_solo()
        if config.ticketZ_printer:
            # ticketZ_tasks_printer.delay(cloture_caisse.ticketZ)
            ticketZ_tasks_printer.delay(cloture_caisse.ticketZ)
            messages.add_message(request, messages.SUCCESS, f"Envoyé sur l'imprimante {config.ticketZ_printer}")
        else:
            ticketZ_tasks_printer(cloture_caisse.ticketZ)
            messages.add_message(request, messages.ERROR,
                                 f"Aucune imprimante selectionnée dans le menu TickerZ des parametres")

        return HttpResponseRedirect(request.query_params.get('next'))


class RecalculerCloture(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk_uuid):
        cloture_caisse = get_object_or_404(ClotureCaisse, pk=pk_uuid)
        start = cloture_caisse.start
        end = cloture_caisse.end

        ticket_z = json.loads(cloture_caisse.ticketZ)
        monnaie_restante = ticket_z.get('dormante_j_rapport')
        monnaie_cadeau_restante = ticket_z.get('dormante_gift_j_rapport')

        # Suppression avant reconstruction
        cloture_caisse.delete()

        # Re Calcul et création de l'object
        # Récupération du PK.
        # L'objet n'est pas disponible, car traitement ordinaire via celery, récupération de string uniquement.
        new_cloture_caise_pk = GetOrCreateRapportFromDate((start.isoformat(), end.isoformat()))
        cloture_caisse = get_object_or_404(ClotureCaisse, pk=new_cloture_caise_pk)

        # La monnaie restante n'est pas calculée par le ticket Z,
        # on la remplace par la dernière valeur connue.
        ticket_z = json.loads(cloture_caisse.ticketZ)
        ticket_z['dormante_j_rapport'] = monnaie_restante
        ticket_z['dormante_gift_j_rapport'] = monnaie_cadeau_restante
        cloture_caisse.ticketZ = json.dumps(ticket_z)
        cloture_caisse.save()

        messages.add_message(request, messages.SUCCESS, f"Re-calcul effectué : {start} au {end}")

        return HttpResponseRedirect(request.query_params.get('next'))


### END NEW METHOD CLOTURE CAISSE

#
# class TicketZapi(APIView):
#     """
#     # Pour la prod billetterie :
#     permission_classes = [HasAPIKey]
#     def get(self, request, pk_uuid):
#         if not billetterie_white_list(request):
#             logger.warning('not billetterie white list')
#             return Response('no no no', status=status.HTTP_401_UNAUTHORIZED)
#     """
#     # Pour le dev et l'impression :
#     permission_classes = [AllowAny]
#
#     def get(self, request, pk_uuid):
#         # date = DateSerializer(data=request.data)
#         # if not date.is_valid():
#         #     return Response(f'{date.errors}', status=status.HTTP_400_BAD_REQUEST)
#
#         rapport = get_object_or_404(RapportTableauComptable, pk=pk_uuid)
#
#         ticketz_validator = TicketZ(rapport=rapport)
#         if ticketz_validator.calcul_valeurs():
#             ticketz_json = ticketz_validator.to_json
#
#             return Response(json.loads(ticketz_json), status=status.HTTP_200_OK)
#         return Response('Erreur json ticketz', status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TicketZFromDatePdf(WeasyTemplateView):
    template_name = "rapports/rapport_complet.html"
    permission_classes = [AllowAny]

    def get_context_data(self, start_date, end_date, **kwargs):
        # On vérifie que les start_date et end_date sont bien des objets datetime
        try:
            assert isinstance(start_date, datetime)
            assert isinstance(end_date, datetime)
        except AssertionError:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise Http404("Date invalide. format accepté : '%Y-%m-%d' ")

        ticketz_validator = TicketZ(start_date=start_date, end_date=end_date)
        if ticketz_validator.calcul_valeurs():
            ticketz = ticketz_validator.to_dict
            self.ticketz = ticketz
            return ticketz

        return Response('Erreur json ticketz', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_pdf_filename(self, **kwargs):
        ticketz = self.ticketz
        return f"Rapport_X.pdf"


class TicketZpdf(WeasyTemplateView):
    template_name = "rapports/rapport_complet.html"
    permission_classes = [AllowAny]

    def get_context_data(self, pk_uuid, **kwargs):
        logger.info(f"{timezone.now()} création de pdf demandé TicketZ. uuid : {pk_uuid}")
        rapport = get_object_or_404(RapportTableauComptable, pk=pk_uuid)

        ticketz_validator = TicketZ(rapport=rapport)
        self.ticketz_validator = ticketz_validator
        if ticketz_validator.calcul_valeurs():
            ticketz = ticketz_validator.to_dict
            return ticketz

    def get_pdf_filename(self, **kwargs):
        ticketz_validator = self.ticketz_validator
        return f"TiBillet_TicketZ_{ticketz_validator.start_date.strftime('%d-%m-%Y')}.pdf"


class TicketZhtml(APIView):
    template_name = "rapports/rapport_complet.html"
    permission_classes = [IsAuthenticated]

    def get(self, request, pk_uuid):
        rapport = get_object_or_404(RapportTableauComptable, pk=pk_uuid)

        ticketz_validator = TicketZ(rapport=rapport)
        if ticketz_validator.calcul_valeurs():
            ticketz = ticketz_validator.to_dict
            return render(request, self.template_name, context=ticketz)

        logger.error(f"Erreur génération du rapport ticketz pour le rapport {rapport}")
        return HttpResponse('Erreur génération du rapport. Contactez un administrateur')


class InvoicePdf(WeasyTemplateView):
    permission_classes = [IsAuthenticated]
    template_name = 'recu_adhesion/recu_adhesion.html'

    def get_context_data(self, pk_uuid, **kwargs):
        logger.info(f"{timezone.now()} création de pdf demandé. uuid : {pk_uuid}")
        config = Configuration.get_solo()
        qr_adhesion = ArticleVendu.objects.filter(commande=pk_uuid, article__methode=config.methode_adhesion)
        if len(qr_adhesion) != 1:
            raise Http404

        adhesion = qr_adhesion[0]
        kwargs['config'] = config
        kwargs['cashless_url'] = settings.LABOUTIK_URL
        kwargs['membre'] = adhesion.membre
        kwargs['adhesion'] = adhesion
        kwargs['uuid4'] = str(pk_uuid).partition('-')[0]

        self.adhesion = adhesion
        self.config = config

        return kwargs

    def get_pdf_filename(self, **kwargs):
        adhesion = self.adhesion
        if adhesion.membre.name and adhesion.membre.prenom and self.config.structure:
            return f'Adhesion_{adhesion.membre.name}_{adhesion.membre.prenom}_{self.config.structure}_{datetime.now().year}.pdf'
        else:
            return f"Adhesion_{datetime.now().year}.pdf"


#### EMAIL ADMIN ACTIVATION
def activate(request, uid, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uid))
        signer = TimestampSigner()
        user_uuid = signer.unsign(uid, max_age=timedelta(hours=24))

        user = get_object_or_404(User, uuid=user_uuid)
        # user = User.objects.get(uuid=user_uuid)

        # On utilise le même algo que pour le reset password
        PR = PasswordResetTokenGenerator()
        is_token_valid = PR.check_token(user, token)

        if is_token_valid:
            user.is_active = True
            user.save()
        else:
            return HttpResponse(_('Token non valide ou expiré'))

    except SignatureExpired:
        return HttpResponse(_('Expired Token'))
    except Exception as e:
        logger.error(e)
        raise e

    if request.method == 'GET':
        return render(request, 'users/password_reset.html', context={'user': user})

    elif request.method == 'POST':
        data = request.POST
        password = data['password']
        try:
            validate_password(password)
        except ValidationError as e:
            return render(request, 'users/password_reset.html', context={'user': user, 'error': e.messages[0]})

        password_confirm = data.get('password_confirm')
        if password != password_confirm:
            error = _("Les mots de passe ne correspondent pas")
            return render(request, 'users/password_reset.html', context={'user': user, 'error': error})

        user.set_password(password)
        staff_group = Group.objects.get(name="staff")
        user.groups.add(staff_group)
        user.save()
        login(request, user)
        return redirect('/')


### BADGEUSE VIEW
#### PLU BESOIN, ON ENVOIE DANS FEDOW DIRECT
# def badgeuse(request, pk_uuid):
#     config = Configuration.get_solo()
#     import ipdb; ipdb.set_trace()
#     config.fedow_domain
#
#     article_badge = Articles.objects.get(methode_choices=Articles.BADGEUSE)
#
#     # Pour l'instant, un seul type de badgeuse.
#     # Si la badgeuse est connecté à un fedow :
#     # if config.can_fedow():
#     # mp_badgeuse = MoyenPaiement.objects.get(categorie=MoyenPaiement.BADGE)
#     # On redirige vers l'interface Fedow
#     # return HttpResponseRedirect(f'{config.fedow_domain}/asset/{mp_badgeuse.id}')
#
#     # Tout les actions de badgeuse sont des articles vendus avec la methode BADGEUSE
#     ligne_badgeuse = (ArticleVendu.objects.filter(article=article_badge)
#                       .order_by('carte__tag_id', 'date_time'))
#
#     dict_carte_passage = {}
#     for ligne in ligne_badgeuse:
#         if ligne.carte not in dict_carte_passage:
#             dict_carte_passage[ligne.carte] = []
#         dict_carte_passage[ligne.carte].append(ligne.date_time)
#
#     passages = []
#     for carte, horaires in dict_carte_passage.items():
#         horaires_sorted = sorted(horaires)
#         if len(horaires_sorted) % 2 != 0:
#             horaires_sorted.append(None)
#         for couple_de_passage in list(zip(horaires_sorted[::2], horaires_sorted[1::2])):
#             passages.append({carte: couple_de_passage})
#
#     context = {
#         'passages': passages,
#         'config': config,
#     }
#     return render(request, 'badgeuse/badgeuse.html', context=context)


### Test templates
@login_required()
def test_email_activation(request):
    # TEST envoie email
    if not settings.DEBUG:
        raise Http404
    template_name = "mails_transactionnels/email_activation.html"
    config = Configuration.get_solo()
    context = {
        'username': request.user.username,
        'user': request.user,
        'now': timezone.now(),
        'title': "Vous avez reçu une invitation pour accéder à l'interface d'administration de TiBillet.",
        'objet': 'Administration Caisse TiBillet',
        'sub_title': 'Décollage imminent',
        'svg_sub_title': '',
        'main_text': f"Vous avez été invité à créer votre compte pour l'administration de l'instance TiBillet de {config.structure}.",
        'main_text_2': "Merci de valider votre email avec le lien ci-dessous. Vous serez invité à créer un mot de passe.",
        'table_info': {},
        'button_color': "#25c19f",  # for tibillet green : "#25c19f", for red warning : "#E8423FFF"
        'button': {
            'text': 'YEAH, Je valide mon email.',
            'url': 'https://www.perdu.com/'
        },
        'next_text_1': "Si vous recevez cet email par erreur, merci de contacter l'équipe de TiBillet",
        'next_text_2': None,
        'end_text': 'A bientôt, et bon voyage',
        'signature': "L'agence spaciale de TiBillet",
    }

    return render(request, template_name, context=context)


@login_required()
def test_new_terminal(request):
    # TEST envoie email
    if not settings.DEBUG:
        raise Http404

    new_terminal = Appareil.objects.all().first()
    if new_terminal:
        if not new_terminal.claimed_at:
            new_terminal.claimed_at = timezone.now()
        if not new_terminal.ip_lan:
            new_terminal.ip_lan = '1.2.3.4'
        if not new_terminal.ip_wan:
            new_terminal.ip_wan = '8.8.8.8'
        if not new_terminal.hostname:
            new_terminal.hostname = 'new_terminal hostname'
        new_terminal.save()
        email_new_hardware(new_terminal.pk)

    ## AFFICHAGE vers /rapport/test_mail/validate/
    template_name = "mails_transactionnels/new_terminal.html"
    ok_circle = "M600 0C268.63 0 0 268.63 0 600s268.63 600 600 600c331.369 0 600-268.63 600-600S931.369 0 600 0zm0 130.371c259.369 0 469.556 210.325 469.556 469.629c0 259.305-210.187 469.556-469.556 469.556c-259.37 0-469.556-210.251-469.556-469.556C130.445 340.696 340.63 130.371 600 130.371zm229.907 184.717L482.153 662.915L369.36 550.122L258.691 660.718l112.793 112.793l111.401 111.401l110.597-110.669l347.826-347.754l-111.401-111.401z"

    context = {
        'username': request.user.username,
        'now': timezone.now(),
        'title': 'Voyage vers la lune',
        'objet': 'Sortie spaciale',
        'sub_title': 'Décollage imminent',
        'svg_sub_title': ok_circle,
        'main_text': "Nous voulions juste vous rappeler votre prochain voyage pour la lune. Assurez-vous d'avoir un scaphandre en état pour une sortie spaciale.",
        'main_text_2': 'deuxieme texte au cazou',
        'table_info': {
            'Date': '12/12/2020',
            'Horaire': '12h00',
            'Lieu': 'Base de lancement Kourou',
        },
        'button_color': "#25c19f",  # for tibillet green : "#25c19f", for red warning : "#E8423FFF"
        'button': {
            'text': 'JE SUIS PRET',
            'url': 'https://www.perdu.com/'
        },
        'next_text_1': "Si vous recevez cet email par erreur, merci de contacter l'équipe de TiBillet",
        'next_text_2': None,
        'end_text': 'A bientôt, et bon voyage',
        'signature': "L'agence spaciale de TiBillet",
    }

    return render(request, template_name, context=context)
