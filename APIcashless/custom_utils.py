import json

import base64
import os

from datetime import datetime, timedelta

import pytz
import requests
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from APIcashless.models import Configuration, MoyenPaiement, Categorie, Articles, PointDeVente
from fedow_connect.utils import rsa_generator, sign_message, sign_utf8_string, get_public_key, get_private_key, \
    rsa_decrypt_string

import logging

logger = logging.getLogger(__name__)

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



def workingdate(datetime_vente=None, config=None, h_start_day=4):
    """
    Fonction qui donne la date en fonction du début de la journée de travail
    Par défault, 4h du matin.

    Exemple :
    - Si la vente se passe à 1h du matin, la date est celle du jour.date - 1 jour.
    - Si la vente se passe à 5h du matin ou 22h le soir, la date est celle du jour.date

    @type datetime_vente: datetime
    """
    if not config:
        config = Configuration.get_solo()
    if not datetime_vente:
        datetime_vente = datetime.now()

    jour = datetime_vente.date()
    tzlocal = pytz.timezone(config.fuseau_horaire)
    debut_jour = tzlocal.localize(datetime.combine(jour, datetime.min.time()), is_dst=None) + timedelta(
        hours=h_start_day)

    # lendemain_quatre_heure = tzlocal.localize(datetime.combine(jour, datetime.max.time()), is_dst=None) + timedelta(
    #     hours=4)

    if datetime_vente < debut_jour:
        # Alors ça s'est passé au petit matin. La date de l'évènement est celle de la veille.
        event = datetime_vente - timedelta(days=1)
        return event.date()
    else:
        return datetime_vente.date()


## NEW

def data_to_b64(data: dict or list) -> bytes:
    data_to_json = json.dumps(data)
    json_to_bytes = data_to_json.encode('utf-8')
    bytes_to_b64 = base64.urlsafe_b64encode(json_to_bytes)
    return bytes_to_b64


def b64_to_data(b64: bytes) -> dict or list:
    b64_to_bytes = base64.urlsafe_b64decode(b64)
    bytes_to_json = b64_to_bytes.decode('utf-8')
    json_to_data = json.loads(bytes_to_json)
    return json_to_data


## OLD

def b64encode(string):
    return base64.urlsafe_b64encode(string.encode('utf-8')).decode('utf-8')


def b64decode(string):
    return base64.urlsafe_b64decode(string).decode('utf-8')


def jsonb64decode(string):
    return json.loads(base64.urlsafe_b64decode(string).decode('utf-8'))


def dict_to_b64(dico: dict):
    dict_to_json = json.dumps(dico)
    json_to_bytes = dict_to_json.encode('utf-8')
    bytes_to_b64 = base64.urlsafe_b64encode(json_to_bytes)
    return bytes_to_b64


def dict_to_b64_utf8(dico: dict):
    return dict_to_b64(dico).decode('utf-8')


## Creation d'objets

def declaration_to_discovery_server():
    # Discovery this serveur to primary

    config = Configuration.get_solo()
    url = settings.LABOUTIK_URL
    if not url:
        raise Exception(_("URL serveur cashless non renseignée "))

    # Création s'il n'existe pas
    public_pem = config.get_public_pem()
    # serveur primaire si non renseigné dans les variables d'environnement
    discovery_serveur = settings.DISCOVERY_URL + 'new_server/'
    discovery_request = requests.post(f'{discovery_serveur}', data={
        'url': url,
        'public_pem': public_pem,
        'locale': settings.LANGUAGE_CODE,
    }, verify=bool(not settings.DEBUG))

    if discovery_request.status_code != 201:
        logger.error(f"Erreur de connexion au serveur discovery pour appareillage : {discovery_request.json()}")
        raise Exception(_(f"Erreur de connexion au serveur discovery pour appareillage : {discovery_request.json()}"))

    discovery_response = discovery_request.json()
    discovery_key = discovery_response.get('key')
    config.set_discovery_key(discovery_key)
    config.save()


def get_pin_on_appareillage(client_name):
    config = Configuration.get_solo()
    if not config.discovery_key:
        raise Exception(_("Clé discovery non renseignée"))
    # serveur primaire si non renseigné dans les variables d'environnement
    discovery_serveur = settings.DISCOVERY_URL

    data = {
        'client_name': client_name
    }

    discovery_new_client_request = requests.post(f'{discovery_serveur}new_client/',
                                                 headers={
                                                     "Authorization": f"Api-Key {config.get_discovery_key()}",
                                                     "Content-type": "application/json",
                                                 },
                                                 data=json.dumps(data),
                                                 verify=bool(not settings.DEBUG))

    if discovery_new_client_request.status_code != 201:
        raise Exception(
            _(f"Erreur de connexion au serveur discovery pour appareillage : {discovery_new_client_request.status_code}"))

    discovery_response = discovery_new_client_request.json()
    return discovery_response['pin_code']


def test_pin_on_appareillage(pin_code: int):
    # Une paire de clé au pif :
    pin_code_str = str(pin_code)
    private_pem, public_pem = rsa_generator()
    signature = sign_utf8_string(
        utf8_string=pin_code_str,
        utf8_private_pem=private_pem)

    data = {
        'pin_code': pin_code_str,
        'public_pem': public_pem,
        'signature': signature,
    }
    discovery_url = settings.DISCOVERY_URL + 'pin_code/'
    claim_request = requests.post(f'{discovery_url}',
                  headers={
                      "Content-type": "application/json",
                  },
                  data=json.dumps(data),
                  verify=bool(not settings.DEBUG))

    assert claim_request.status_code == 200
    claim_data = claim_request.json()
    enc_server_url = claim_data['server_url']
    private_key = get_private_key(private_pem)
    serveur_url = rsa_decrypt_string(enc_server_url, private_key)

    config = Configuration.get_solo()
    assert serveur_url == settings.CAS

    confirmation_public_pem = get_public_key(claim_data['server_public_pem'])
    config_public_key = config.get_public_key()
    assert confirmation_public_pem.public_numbers() == config_public_key.public_numbers()




def badgeuse_creation():
    # L'article badgeuse vient de lespass
    """
    if not MoyenPaiement.objects.filter(categorie=MoyenPaiement.BADGE).exists():
        mp_badge = MoyenPaiement.objects.create(
            categorie=MoyenPaiement.BADGE,
            name=_('Badge'),
        )

    if not Articles.objects.filter(methode_choices=Articles.BADGEUSE).exists():
        categorie_badge, created = Categorie.objects.get_or_create(
            name="Badge",
            icon='fa-id-badge',
        )
        article_badgeur, created = Articles.objects.get_or_create(name=_("Badger"),
                                                                  methode_choices=Articles.BADGEUSE,
                                                                  categorie=categorie_badge)
    """
    pass
