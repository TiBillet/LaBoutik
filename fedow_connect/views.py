import base64
import requests
from django.conf import settings
from django.utils import timezone
from rest_framework_api_key.models import APIKey

from APIcashless.custom_utils import jsonb64decode, dict_to_b64_utf8, dict_to_b64
from APIcashless.models import Configuration


import logging

from fedow_connect.tasks import after_handshake
from fedow_connect.utils import sign_message, verify_signature, data_to_b64

logger = logging.getLogger(__name__)



def handshake(config: Configuration):
    # Le handshake se lance lorsqu'une clé FEDOW est entré dans le menu de configuration
    # On récupère la clé publique de cette instance LaBoutik.
    # Si elle n'existe pas, la fonction la génère
    ip_cashless = config.ip_cashless
    get_public_pem = config.get_public_pem()
    dokos_id = config.dokos_id
    string_connect = config.string_connect

    # La string est encodée en base64, on la décode
    # Récupération de l'adresse, de la clé api temporaire,
    # et de l'uuid correspondant à lieux qui a fait la demande de connection au FEDOW
    decoded_data = jsonb64decode(string_connect)

    fedow_domain = decoded_data['domain']
    fedow_place_uuid = decoded_data['uuid']
    fedow_key = decoded_data['temp_key']
    # Création de la clé API pour cette instance serveur LaBoutik
    api_key, key = APIKey.objects.create_key(name="fedow_key")

    # Toutes les infos sont ok pour le handshake, on renvoie la clé API et la clé publique RSA
    # Dictionnaire de réponse. On renvoie l'uuid avec la signature de fedow
    handshake_data = {
        "fedow_place_uuid": f"{fedow_place_uuid}",
        "cashless_ip": f"{ip_cashless}",
        "cashless_url": f"{settings.LABOUTIK_URL}",
        "cashless_admin_apikey": f"{key}",
        "cashless_rsa_pub_key": f"{get_public_pem}",
        "dokos_id": f"{dokos_id}",
    }

    # Signature du dictionnaire pour s'assurer que le FEDOW utilise bien la même méthode de signature
    # car il devra la valider pour continuer le handshake.
    signature = sign_message(
        dict_to_b64(handshake_data),
        config.get_private_key()).decode('utf-8')

    # Ici, on s'auto vérifie :
    if not verify_signature(config.get_public_key(),
                            dict_to_b64(handshake_data),
                            signature):
        raise Exception("Erreur de signature")

    # Envoie de la requete à FEDOW : Dictionnaire + signature
    session = requests.Session()
    request_fedow = session.post(
        f"https://{fedow_domain}/place/handshake/",
        headers={
            "Authorization": f"Api-Key {fedow_key}",
            "Signature": f"{signature}"
        },
        data=handshake_data,
        verify=bool(not settings.DEBUG),
    )
    session.close()

    # Le retour du FEDOW est un code 202 si tout est ok
    # Handshake ok, on décode la réponse
    if request_fedow.status_code == 202:
        decoded_return_handshake = jsonb64decode(request_fedow.content)
        place_admin_apikey = decoded_return_handshake.get('place_admin_apikey')
        url_onboard = decoded_return_handshake.get('url_onboard')
        place_wallet_uuid = decoded_return_handshake.get('place_wallet_uuid')

        if key and place_wallet_uuid :
            config.fedow_place_admin_apikey = place_admin_apikey
            config.onboard_url = url_onboard
            config.fedow_domain = fedow_domain
            config.fedow_place_uuid = fedow_place_uuid
            config.fedow_place_wallet_uuid = place_wallet_uuid
            config.save()

            return True


    # Raise erreur si le code n'est pas 202
    logger.error(f"{timezone.localdate()} - erreur handkshake : {request_fedow.status_code} {request_fedow.content}")
    raise Exception(f"Erreur de handshake : {request_fedow.status_code} {request_fedow.content}")
