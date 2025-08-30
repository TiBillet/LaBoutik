import decimal
import json
import logging
import os, time
import smtplib
from datetime import datetime
from uuid import uuid4

import dateutil.parser
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.defaultfilters import slugify
from django.template.loader import get_template, render_to_string
from django.utils import timezone
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework.exceptions import NotAcceptable
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

from APIcashless.models import ArticleVendu, Configuration, Assets, \
    Articles, MoyenPaiement, ClotureCaisse, CarteCashless, Place, PointDeVente, dround, Membre, Appareil
from Cashless.celery import app
from administration.ticketZ import TicketZ
from odoo_api.odoo_api import OdooAPI
from tibiauth.models import TibiUser
from webview.validators import DataAchatDepuisClientValidator
from webview.views import Commande
from django.utils.translation import gettext_lazy as _
from django.core.signing import TimestampSigner

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


def determine_interval(start_date, end_date):
    interval = end_date - start_date

    if interval.days >= 32:  # Plus d'un mois
        return ClotureCaisse.ANNUEL
    elif interval.days >= 8:  # Plus d'une semaine
        return ClotureCaisse.MENSUEL
    elif interval.days >= 2:  # Plus d'un jour
        return ClotureCaisse.HEBDOMADAIRE
    else:
        return ClotureCaisse.CLOTURE


@app.task()
def badgeuse_to_dokos(article_vendu_pk):
    config = Configuration.get_solo()
    url_dokos = config.dokos_url
    cle_dokos = config.dokos_key
    dokos_id = config.dokos_id
    dokos_id_origine = dokos_id

    if not all([url_dokos, cle_dokos, dokos_id]):
        logger.info(f"badgeuse_to_dokos : pas de config dokos")
        return None

    article_vendu = ArticleVendu.objects.get(pk=article_vendu_pk)
    carte: CarteCashless = article_vendu.carte

    membre = carte.membre
    if not carte:
        logger.error(f"badgeuse_to_dokos : pas de carte")
        raise NotAcceptable(detail=f"badgeuse_to_dokos : pas de carte", code=None)

    # Si l'origine de la carte est d'ailleurs, on prends l'id du lieu d'origine
    if carte.origin:
        if carte.origin.place:
            place: Place = carte.origin.place
            dokos_id_origine = place.dokos_id if place.dokos_id else config.dokos_id

    if not membre:
        logger.error(f"badgeuse_to_dokos : pas de membre")
        raise NotAcceptable(detail=f"badgeuse_to_dokos : pas de membre", code=None)

    if not membre.email:
        logger.error(f"badgeuse_to_dokos : pas d'email")
        raise NotAcceptable(detail=f"badgeuse_to_dokos : pas d'email", code=None)

    session = requests.Session()
    url = f"{url_dokos}api/method/venues_federation.api.v1/checkin"
    headers = {
        'Authorization': f'token {cle_dokos}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    reponse_dokos = session.post(url, headers=headers, json={
        "client_venue": f"{dokos_id_origine}",
        "provider_venue": f'{dokos_id}',
        "user": f"{membre.email}"})

    logger.info(f"badgeuse_to_dokos : {reponse_dokos.status_code} {reponse_dokos.content}")
    if reponse_dokos.status_code != 200:
        logger.error(f"methode_BG : erreur dokos {reponse_dokos} {reponse_dokos.content}")
        raise NotAcceptable(detail=f"{reponse_dokos.status_code}", code=None)

    logger.info(f"badgeuse_to_dokos : {reponse_dokos.status_code} {reponse_dokos.content}")
    return reponse_dokos


@app.task
def adhesion_to_odoo(article_vendu_pk: int):
    odoo_api = OdooAPI()
    odoo_api.new_membership(ArticleVendu.objects.get(pk=article_vendu_pk))


@app.task
def cashback(article_vendu_pk):
    time.sleep(2) # pour laisser l'article vendu se rentrer en DB
    config = Configuration.get_solo()
    article_vendu = ArticleVendu.objects.get(pk=article_vendu_pk)
    if article_vendu.article.methode_choices == Articles.RECHARGE_EUROS and config.cashback_active:
        total = article_vendu.total()
        if total >= config.cashback_start \
                and config.cashback_value > 0 \
                and article_vendu.carte:
            logger.info(f"TRIGGER CASHBACK RECHARGE EURO STRIPE")

            # On multiplie si la recharge est 2x le montant du start
            qty = config.cashback_value * int(total / config.cashback_start)

            carte = article_vendu.carte
            asset_principal_cadeau, created = carte.assets.get_or_create(
                monnaie=MoyenPaiement.LOCAL_GIFT)

            exqty = asset_principal_cadeau.qty
            asset = Assets.objects.filter(pk=asset_principal_cadeau.pk)
            asset.update(qty=exqty + qty)
            logger.info(f"    carte assets : {carte.assets.all()}")

            article = Articles.objects.get(prix=1, methode_choices=Articles.RECHARGE_CADEAU)

            ArticleVendu.objects.create(
                article=article,
                prix=article.prix,
                qty=qty,
                pos=article_vendu.pos,
                carte=carte,
                membre=article_vendu.membre,
                responsable=article_vendu.responsable,
                moyen_paiement=None,
                commande=article_vendu.commande,
                uuid_paiement=article_vendu.uuid_paiement,
                table=article_vendu.table,
                ip_user=article_vendu.ip_user,
            )


@app.task
def fidelity_task(article_vendu_pk):
    # Mecanisme qui incrémente la valeur d'un asset pour une dépense d'un autre asset.
    article_vendu = ArticleVendu.objects.get(pk=article_vendu_pk)

    config = Configuration.get_solo()
    if not all([
        config.fidelity_active,
        config.fidelity_asset,
        article_vendu.moyen_paiement in config.fidelity_asset_trigger.all(),
        article_vendu.carte,
    ]):
        logger.info(f"TRIGGER FIDELITY : Pas de config FIDELITY")
        return None

    logger.info(f"TRIGGER FIDELITY")
    # Recherche du MoyenPaiement Fidelity :
    fidelity_asset = config.fidelity_asset
    article_fidelite, created = Articles.objects.get_or_create(
        name=_("Point de fidélité"),
        prix=1, methode_choices=Articles.FIDELITY)
    # Carte :
    carte = article_vendu.carte
    # On détermine le nombre de points à ajouter
    qty = dround(article_vendu.total() * config.fidelity_factor)
    # On détermine l'asset à incrémenter
    asset, created = carte.assets.get_or_create(monnaie=fidelity_asset)

    # Fabrication de la requete pour incrémenter
    # On passe par la même méthode que tout le reste
    data_ext = {
        "pk_responsable": Membre.objects.get_or_create(name="FIDELITY")[0].pk,
        "pk_pdv": PointDeVente.objects.filter(name="Cashless")[0].pk,
        "tag_id": carte.tag_id,
        "moyen_paiement": fidelity_asset.categorie,
        "total": qty,
        "articles": [{
            'pk': article_fidelite.pk,
            'qty': qty,
        }, ],
    }
    validator_transaction = DataAchatDepuisClientValidator(data=data_ext)
    if validator_transaction.is_valid():
        data = validator_transaction.validated_data
        commande = Commande(data)
        commande_valide = commande.validation()


@app.task(
    bind=True,
    default_retry_delay=2,
    retry_backoff=True,
    max_retries=10)
def test_retry():
    pass


class CeleryMailerClass():

    def __init__(self,
                 email: str,
                 title: str,
                 text=None,
                 html=None,
                 template=None,
                 context=None,
                 attached_files=None,
                 ):

        self.title = title
        self.email = email
        self.text = text
        self.html = html
        self.context = context
        self.attached_files = attached_files
        self.sended = None

        if template and context:
            self.html = render_to_string(template, context=context)

    def config_valid(self):
        EMAIL_HOST = os.environ.get('EMAIL_HOST')
        EMAIL_PORT = os.environ.get('EMAIL_PORT')

        # not required if local mail server :
        # EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
        # EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

        # raise error if not DEFAULT nor HOST
        self.return_email = os.environ.get('DEFAULT_FROM_EMAIL',  os.environ['EMAIL_HOST_USER'] )

        if all([
            EMAIL_HOST,
            EMAIL_PORT,
            self.return_email,
            self.title,
            self.email,
        ]):
            return True
        else:
            return False

    def send(self):
        if self.html and self.config_valid():

            logger.info(f'  WORKDER CELERY : send_mail {self.email} - {self.title}')
            mail = EmailMultiAlternatives(
                self.title,
                self.text,
                self.return_email,
                [self.email, ],
            )
            mail.attach_alternative(self.html, "text/html")

            # import ipdb; ipdb.set_trace()
            if self.attached_files:
                for filename, file in self.attached_files.items():
                    if ".pdf" in filename:
                        mail.attach(filename, file, 'application/pdf')
                    elif ".html" in filename:
                        mail.attach(filename, file, 'text/html')
                    else:
                        mail.attach(filename, file, 'text/plain')

            mail_return = mail.send(fail_silently=False)

            if mail_return == 1:
                self.sended = True
                logger.info(f'  WORKDER CELERY : mail sended')

            else:
                logger.error(f'     WORKER CELERY mail non envoyé : {mail_return} - {self.email}')

            return mail_return
        else:
            logger.error(f'Pas de contenu HTML ou de configuration email valide')
            raise ValueError('Pas de contenu HTML ou de configuration email valide')


@app.task
def envoie_rapport_et_ticketz_par_mail(cloture_pk=None):
    configuration = Configuration.get_solo()
    structure_name = configuration.structure

    cloture = ClotureCaisse.objects.get(pk=cloture_pk)
    start = timezone.localtime(cloture.start)
    end = timezone.localtime(cloture.end)
    name_cloture = f"{start.strftime('%Y-%m-%d-%Hh%M')}-a-" \
                   f"{end.strftime('%Y-%m-%d-%Hh%M')}-" \
                   f"{slugify(cloture.get_categorie_display())}-" \
                   f"{slugify(structure_name)}"

    ticket_z_dict = json.loads(cloture.ticketZ)

    attached_files = {}

    rapport_html_binary = template_to_html_file('rapports/rapport_complet.html', ticket_z_dict)
    attached_files[f"{name_cloture}-rapport.html"] = rapport_html_binary
    ticketz_html_binary = template_to_html_file('rapports/ticketZ_simple.html', ticket_z_dict)
    attached_files[f"{name_cloture}-ticketz.html"] = ticketz_html_binary

    # Génération du fichier .pdf à envoyer en pièce jointe
    # Le tableau des ventes est trop gros pour le pdf. Faudra trouver une autre solution.
    # rapport_pdf = template_to_pdf('rapports/rapport_complet.html', ticket_z_dict)
    # attached_files[f"{name_cloture}-rapport.pdf"] = rapport_pdf
    ticketz_pdf = template_to_pdf('rapports/ticketZ_simple.html', ticket_z_dict)
    attached_files[f"{name_cloture}-ticketz.pdf"] = ticketz_pdf

    email = configuration.compta_email if configuration.compta_email else configuration.email

    text_subject = f"{cloture.get_categorie_display()} du {start.strftime('%Y-%m-%d-%Hh%M')} au {end.strftime('%Y-%m-%d-%Hh%M')}"

    try:
        context = {
            'organisation': f'{structure_name}',
            'start': f'{start.strftime("%Y-%m-%d à %Hh%M")}',
            'end': f'{end.strftime("%Y-%m-%d à %Hh%M")}',
        }

        mail = CeleryMailerClass(
            email,
            f"{text_subject}",
            template='rapports/mail_rapport.html',
            context=context,
            attached_files=attached_files,
        )
        mail.send()
        logger.info(f"    envoie_rapport_et_ticketz_par_mail : mail.sended : {mail.sended}")

    except smtplib.SMTPRecipientsRefused as e:
        logger.error(
            f"ERROR {timezone.now()} Erreur mail SMTPRecipientsRefused pour report_celery_mailer : {e}")


@app.task
def email_activation(user_uuid: uuid4=None):
    config = Configuration.get_solo()
    User: TibiUser = get_user_model()
    user = User.objects.get(uuid=user_uuid)
    # On utilise un timestamps signer pour vérifier la date de création du lien
    signer = TimestampSigner()
    uid = urlsafe_base64_encode(force_bytes(signer.sign(f'{user_uuid}')))
    token = default_token_generator.make_token(user)
    connexion_url = f"{settings.LABOUTIK_URL}rapport/activate/{uid}/{token}/"
    logger.warning(f'{connexion_url}')

    template_name = "mails_transactionnels/email_activation.html"
    email = user.email
    subject = _("Vous avez reçu une invitation pour accéder à l'interface d'administration de TiBillet.")
    context = {
        'username': user.username,
        'user': user,
        'now': timezone.now(),
        'title': subject,
        'objet': _('Administration Caisse TiBillet'),
        'sub_title': _('Décollage imminent'),
        'svg_sub_title': '',
        'main_text': _(f"Vous avez été invité à créer votre compte pour l'administration de l'instance TiBillet de ") + f"{config.structure}.",
        'main_text_2': _("Merci de valider votre email avec le lien ci-dessous. Vous serez invité à créer un mot de passe."),
        'table_info': {},
        'button_color': "#25c19f",  # for tibillet green : "#25c19f", for red warning : "#E8423FFF"
        'button': {
            'text': _('Je valide mon email'),
            'url': f'{connexion_url}'
        },
        'next_text_1': _("Si vous recevez cet email par erreur, merci de contacter l'équipe de TiBillet"),
        'next_text_2': None,
        'end_text': _('A bientôt, et bon voyage'),
        'signature': _("L'agence spaciale de TiBillet"),
    }

    try :
        mail = CeleryMailerClass(
            email,
            f"{subject}",
            template=template_name,
            context=context,
            attached_files=None,
        )
        mail.send()
        logger.info(f"    envoie_rapport_et_ticketz_par_mail : mail.sended : {mail.sended}")

    except smtplib.SMTPRecipientsRefused as e:
        logger.error(
            f"ERROR {timezone.now()} Erreur mail SMTPRecipientsRefused pour report_celery_mailer : {e}")
    except Exception as e :
        logger.error(
            f"ERROR {timezone.now()} Erreur mail pour report_celery_mailer : {e}")
        # TODO: A virer lorsque probleme de mail réglé :
        logger.warning(f'{connexion_url}')


@app.task
def email_new_hardware(appareil_pk=None):
    configuration = Configuration.get_solo()
    structure_name = configuration.structure
    domain = settings.LABOUTIK_URL
    # domain = configuration.domaine_cashless
    email = configuration.email

    appareil: Appareil = Appareil.objects.get(pk=appareil_pk)
    ipinfo = requests.get(f'https://ipinfo.io/{appareil.ip_wan}/').json()
    logger.info(appareil.ip_wan)
    logger.info(ipinfo)

    try:
        template_name = "mails_transactionnels/new_terminal.html"
        subject = _(f"Un nouveau terminal '{appareil.name}' s'est connecté à votre instance TiBillet {structure_name}")

        context = {
            'username': email,
            'now': timezone.now(),
            'title': subject,
            'objet': 'Nouveau terminal activé',
            'sub_title': "Ceci est un e-mail d'information.",
            'main_text': "Un nouveau terminal s'est connecté à votre instance TiBillet. Si vous pensez que cette demande n'est pas légitime, "
                         "veuillez vérifier les informations suivantes.",
            'main_text_2': "Si vous pensez que cette demande est légitime, vous n'avez rien a faire de plus :)",
            'main_text_3': "Dans le cas contraire, vous pouvez desactiver le terminal via le bouton ci dessous. Merci de contacter l'équipe d'administration via : contact@tibillet.re au moindre doute.",
            'table_info': {
                'Serveur': domain,
                'Name': appareil.name,
                'Date': appareil.claimed_at.strftime("%Y-%m-%d"),
                'Horaire': appareil.claimed_at.astimezone().strftime("%Hh%M"),
                'Version': appareil.version,
                'Hostname': appareil.hostname,
                'User agent': appareil.user_agent,
                'IP Wan': appareil.ip_wan,
                'Lieu': f'{ipinfo["city"]} ({ipinfo["country"]})',
                'IP Lan': appareil.ip_lan,
            },
            'button_color': "#E8423FFF",
            'button': {
                'text': 'ANNULER LA CONNEXION',
                'url': f'{domain}adminstaff/APIcashless/appareil/'
            },
            'next_text_1': "Si vous recevez cet email par erreur, merci de contacter l'équipe de TiBillet",
            'next_text_2': None,
            'end_text': 'A bientôt, et bon voyage',
            'signature': "Marvin, le robot de TiBillet",
        }

        mail = CeleryMailerClass(
            email,
            f"{subject}",
            template=template_name,
            context=context,
            attached_files=None,
        )
        mail.send()
        logger.info(f"    envoie_rapport_et_ticketz_par_mail : mail.sended : {mail.sended}")

    except smtplib.SMTPRecipientsRefused as e:
        logger.error(
            f"ERROR {timezone.now()} Erreur mail SMTPRecipientsRefused pour report_celery_mailer : {e}")


def template_to_pdf(template_name, context: dict):
    template = get_template(template_name)
    html = template.render(context)

    font_config = FontConfiguration()
    pdf_binary = HTML(string=html).write_pdf(
        font_config=font_config,
    )
    return pdf_binary


def template_to_html_file(template_name, context: dict):
    """ Génère un fichier .html binaire à partir d'un ticketZ en html """
    template = get_template(template_name)
    html = template.render(context)

    return str.encode(html)


@app.task
def GetOrCreateRapportFromDate(dates):
    start_date = dates[0]
    end_date = dates[1]
    if not isinstance(dates[0], datetime) or not isinstance(dates[1], datetime):
        start_date = dateutil.parser.parse(dates[0])
        end_date = dateutil.parser.parse(dates[1])

    try:
        cloture_caisse = ClotureCaisse.objects.get(start=start_date, end=end_date)
        logger.info("Cloture de caisse existe déja.")
        return cloture_caisse.pk

    except ClotureCaisse.DoesNotExist:
        # Génération du ticket Z
        ticketz_validator = TicketZ(start_date=start_date, end_date=end_date, calcul_dormante_from_date=True)
        if ticketz_validator.calcul_valeurs():
            ticketz_json = ticketz_validator.to_json

            cloture_caisse = ClotureCaisse.objects.create(
                ticketZ=ticketz_json,
                start=start_date,
                end=end_date,
                categorie=determine_interval(start_date, end_date),
            )

            # Le rapport est nouveau donc envoyé par mail
            envoie_rapport_et_ticketz_par_mail.delay(cloture_caisse.pk)

            return cloture_caisse.pk

    except Exception as e:
        logger.error(f"GetOrCreateRapportFromDate Erreur lors de la création du rapport : {e}")
        raise e
