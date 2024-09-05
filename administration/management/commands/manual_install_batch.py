import requests
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from faker import Faker

from APIcashless.custom_utils import jsonb64decode
from APIcashless.models import *
from APIcashless.tasks import email_activation
from fedow_connect.tasks import after_handshake
from fedow_connect.utils import get_public_key, rsa_encrypt_string, rsa_decrypt_string, data_to_b64
from fedow_connect.views import handshake

logger = logging.getLogger(__name__)

### SUR FEDOW :
# Pour cleaner un lieu avant le onboard
place = Place.objects.get(name='labricc')
place.cashless_server_url = None
place.save()

# Archiver les wallet
from fedow_core.models import Place, Configuration, get_or_create_user, OrganizationAPIKey, wallet_creator
assets = Asset.objects.filter(wallet_origin=place.wallet)
# exemple pour archiver tout sauf l'adhésion
adh = assets.first() # vérifier que c'est bien l'adhésion

assets_a_sup = assets.exclude(pk=adh.pk)
wallet_archive = wallet_creator(name='archive')
assets_a_sup.update(wallet_origin=wallet_archive)
### SUR LESPASS

# Pour cleaner un lieu avant le onboard
config = Configuration.get_solo()
config.server_cashless, config.key_cashless = None, None
config.save()

### SUR LABOUTIK

main_asset = os.environ['MAIN_ASSET_NAME']
admin_email = os.environ['ADMIN_EMAIL']
fedow_url = os.environ['FEDOW_URL']
lespass_url = os.environ['LESPASS_TENANT_URL']
config = Configuration.get_solo()
config.email = os.environ['ADMIN_EMAIL']
config.billetterie_url = os.environ['LESPASS_TENANT_URL']
config.fedow_domain = os.environ['FEDOW_URL']

hello_lespass = requests.post(f'{lespass_url}api/get_user_pub_pem/',
                              data={
                                  "email": f"{os.environ['ADMIN_EMAIL']}",
                              },
                              verify=bool(not settings.DEBUG))

lespass_admin_pub_pem = hello_lespass.json()['public_pem']
lespass_admin_public_key = get_public_key(lespass_admin_pub_pem)

api_key, key = APIKey.objects.create_key(name="billetterie_key")
config.key_billetterie = api_key

# Handshake Lespass :
handshake_lespass = requests.post(f'{lespass_url}api/onboard_laboutik/',
                                  data={
                                      "server_cashless": f"https://{os.environ['DOMAIN']}",
                                      "key_cashless": f"{rsa_encrypt_string(utf8_string=key, public_key=lespass_admin_public_key)}",
                                      "pum_pem_cashless": f"{config.get_public_pem()}",
                                      "email": f"{os.environ['ADMIN_EMAIL']}",
                                  },
                                  verify=bool(not settings.DEBUG))

# Le serveur LesPass renvoie la clé pour se connecter à Fedow, chiffrée avec une clé Fernet aléatoire
# La clé fernet qui déchiffre le json :
handshake_lespass_data = handshake_lespass.json()
cypher_rand_key = handshake_lespass_data['cypher_rand_key']
fernet_key = rsa_decrypt_string(utf8_enc_string=cypher_rand_key, private_key=config.get_private_key())
cypher_json_key_to_cashless = handshake_lespass_data['cypher_json_key_to_cashless']

# from cryptography.fernet import Fernet
decryptor = Fernet(fernet_key)
config.string_connect = decryptor.decrypt(cypher_json_key_to_cashless.encode('utf-8')).decode('utf8')
config.billetterie_url = lespass_url
# Le nom de la structure est le même que le tenant

config.structure = handshake_lespass_data.get('organisation_name')

config.siret = handshake_lespass_data.get('siren')
config.adresse = (f"{handshake_lespass_data.get('adress')} "
                  f"{handshake_lespass_data.get('postal_code')} "
                  f"{handshake_lespass_data.get('city')}")
config.telephone = handshake_lespass_data.get('phone')
config.numero_tva = handshake_lespass_data.get('tva_number')

hello_fedow = requests.get(f'{fedow_url}helloworld/',
                           verify=bool(not settings.DEBUG))
decoded_data = jsonb64decode(config.string_connect)

# ipbill = '51.77.151.34'
config.ip_cashless = '51.38.81.101'
config.save()
logger.info("Lespass Plugged !")

### Fedow handshake :
fedow_handshake = handshake(config)
# after handshake
Origin.objects.all().delete()
Place.objects.all().delete()
MoyenPaiement.objects.filter(categorie=MoyenPaiement.STRIPE_FED).delete()
MoyenPaiement.objects.filter(categorie=MoyenPaiement.EXTERNAL_MEMBERSHIP).delete()

