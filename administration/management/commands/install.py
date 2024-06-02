import json
import logging
import os
import random
import socket
import sys
from time import sleep
from uuid import UUID

import requests
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand

from APIcashless.custom_utils import badgeuse_creation, declaration_to_discovery_server, jsonb64decode
from APIcashless.models import *
from APIcashless.tasks import email_activation
from fedow_connect.tasks import after_handshake
from fedow_connect.utils import get_public_key, rsa_encrypt_string, rsa_decrypt_string, data_to_b64
from fedow_connect.views import handshake
from faker import Faker

logger = logging.getLogger(__name__)


# TODO: rajouter les carte depuis le .env DEMO

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--tdd',
                            action='store_true',
                            help='Demo data for Test drived dev')

    def handle(self, *args, **options):
        class Install(object):
            def __init__(self, options):
                self.main_asset = os.environ['MAIN_ASSET_NAME']
                self.admin_email = os.environ['ADMIN_EMAIL']
                self.fedow_url = os.environ['FEDOW_URL']

                # Au format https://fedow.tibillet.localhost/
                if not self.fedow_url.endswith("/"):
                    self.fedow_url += "/"
                if not self.fedow_url.startswith("https://"):
                    raise Exception("Fedow URL must start with https://")

                self.lespass_url = os.environ['LESPASS_TENANT_URL']

                # Les variables du fichier env dans config
                self.config = self._base_config(options)

                # Avant toute installation, on vérifie que Lespass et Fedow existent

                self.lespass_handshake = self._lespass_handshake()
                self.fedow_handshake = self._fedow_handshake()

                # Local and gift asset
                self.assets_fedow = self._assets_fedow()
                # Cash, Credit card, stripe, oceco
                self.assets_no_fedow = self._assets_no_fedow()

                self.methode_articles = self._methode_articles()
                self.configuration = self._configuration()

                self.couleur = self._couleur()

                self.articles_generiques = self._articles_generiques()
                self.pdv_cashless = self._point_de_vente_cashless()

                self.admin = self._create_admin_from_env_email()

                if options.get('tdd'):
                    self.set_admin_user_active()
                    self.pop_membre_articles_cartes_test()
                    self.pop_articles_test()
                    self.pop_tables_test()
                    self.preparation_test()
                    self.printer_test()
                    self.add_membership_and_badge_articles()
                    # badgeuse_creation()

            def _base_config(self, options):
                config = Configuration.get_solo()
                config.email = os.environ['ADMIN_EMAIL']
                config.billetterie_url = os.environ['LESPASS_TENANT_URL']
                config.fedow_domain = os.environ['FEDOW_URL']

                if not options.get('tdd'):
                    config.save()
                    return config

                # MODE DEV/DEMO
                # config.prix_adhesion = os.environ.get('PRIX_ADHESION', 13)
                config.appareillement = True
                config.validation_service_ecran = True
                config.remboursement_auto_annulation = True

                # Ip du serveur cashless et du ngnix dans le même réseau ( env de test )
                self_ip = socket.gethostbyname(socket.gethostname())
                templist: list = self_ip.split('.')
                templist[-1] = 1
                config.ip_cashless = '.'.join([str(ip) for ip in templist])
                config.billetterie_ip_white_list = '.'.join([str(ip) for ip in templist])

                # Parfois l'ip prise est le 192...
                # config.ip_cashless = "172.21.0.1"
                # config.billetterie_ip_white_list = "172.21.0.1"

                config.save()
                return config


            def _assets_fedow(self):
                mp = {}
                mp['principale'] = MoyenPaiement.objects.get_or_create(name=self.main_asset,
                                                                       blockchain=True,
                                                                       categorie=MoyenPaiement.LOCAL_EURO,
                                                                       )[0]

                mp['cadeau'] = MoyenPaiement.objects.get_or_create(name=f"{self.main_asset} Cadeau",
                                                                   cadeau=True,
                                                                   blockchain=True,
                                                                   categorie=MoyenPaiement.LOCAL_GIFT,
                                                                   )[0]

                return mp

            def _assets_no_fedow(self):
                d = {}
                d['espece'] = \
                    MoyenPaiement.objects.get_or_create(name="Espece", blockchain=False, categorie=MoyenPaiement.CASH)[
                        0]
                d['carte_bancaire'] = MoyenPaiement.objects.get_or_create(name="Carte bancaire", blockchain=False,
                                                                          categorie=MoyenPaiement.CREDIT_CARD_NOFED)[0]
                d['commande'] = MoyenPaiement.objects.get_or_create(name="Commande", blockchain=False,
                                                                    categorie=MoyenPaiement.COMMANDE)[0]
                d['stripe'] = MoyenPaiement.objects.get_or_create(name="Web (Stripe)", blockchain=False,
                                                                  categorie=MoyenPaiement.STRIPE_NOFED)[0]
                d['oceco'] = MoyenPaiement.objects.get_or_create(name="Web (Oceco)", blockchain=False,
                                                                 categorie=MoyenPaiement.OCECO)[0]

                return d

            def _methode_articles(self):
                d = {}
                d['vente_article'] = Methode.objects.get_or_create(name="VenteArticle")[0]
                d['vider_carte'] = Methode.objects.get_or_create(name="ViderCarte")[0]
                # d['adhesion'] = Methode.objects.get_or_create(name="Adhesion")[0]
                d['ajout_monnaie_virtuelle'] = Methode.objects.get_or_create(name="AjoutMonnaieVirtuelle")[0]
                d['ajout_monnaie_virtuelle_cadeau'] = Methode.objects.get_or_create(
                    name="AjoutMonnaieVirtuelleCadeau")[0]
                d['retour_consigne'] = Methode.objects.get_or_create(name="RetourConsigne")[0]
                d['paiement_fractionne'] = Methode.objects.get_or_create(name="PaiementFractionne")[0]

                return d

            def _configuration(self):
                cache.clear()
                configuration = Configuration.get_solo()
                # Crash if doesn't exist. It's OK
                configuration.domaine_cashless = settings.LABOUTIK_URL

                # configuration.prix_adhesion = self.prix_adhesion

                configuration.monnaie_principale = self.assets_fedow.get('principale')
                configuration.monnaie_principale_cadeau = self.assets_fedow.get('cadeau')
                configuration.moyen_paiement_espece = self.assets_no_fedow.get('espece')
                configuration.moyen_paiement_cb = self.assets_no_fedow.get('carte_bancaire')
                configuration.moyen_paiement_mollie = self.assets_no_fedow.get('stripe')
                configuration.moyen_paiement_oceco = self.assets_no_fedow.get('oceco')
                configuration.moyen_paiement_commande = self.assets_no_fedow.get('commande')

                for key, monnaie in self.assets_fedow.items():
                    configuration.monnaies_acceptes.add(monnaie)

                configuration.monnaies_acceptes.add(
                    configuration.monnaie_principale,
                    configuration.monnaie_principale_cadeau,
                )

                configuration.methode_vente_article = self.methode_articles.get('vente_article')
                configuration.methode_ajout_monnaie_virtuelle = self.methode_articles.get('ajout_monnaie_virtuelle')
                configuration.methode_ajout_monnaie_virtuelle = self.methode_articles.get(
                    'ajout_monnaie_virtuelle_cadeau')
                # configuration.methode_adhesion = self.methode_articles.get('adhesion')
                configuration.methode_retour_consigne = self.methode_articles.get('retour_consigne')
                configuration.methode_vider_carte = self.methode_articles.get('vider_carte')
                configuration.methode_paiement_fractionne = self.methode_articles.get('paiement_fractionne')

                # configuration.emplacement = self.data.get("main_asset")

                configuration.save()

                return configuration

            def _articles_generiques(self):

                d = {}
                CatCashless = Categorie.objects.get_or_create(
                    name="Cashless",
                    icon='fa-euro-sign',
                    cashless=True,
                    couleur_backgr=Couleur.objects.get(name='Orange'),
                )[0]

                CatConsigne = Categorie.objects.get_or_create(
                    name="Consigne",
                    icon='fa-recycle',
                    couleur_backgr=Couleur.objects.get(name='White'),
                    couleur_texte=Couleur.objects.get(name='Black'),
                )[0]

                CatCadeau = Categorie.objects.get_or_create(
                    name="Cadeau",
                    icon='fa-gift',
                    cashless=True,
                    couleur_backgr=Couleur.objects.get(name='Fuchsia')
                )[0]

                CatDanger = Categorie.objects.get_or_create(
                    name="Danger",
                    icon="fa-radiation",
                    cashless=True,
                    couleur_backgr=Couleur.objects.get(name='Red')
                )[0]

                d["+0.1"] = \
                    Articles.objects.get_or_create(name="+0.1",
                                                   prix=0.1,
                                                   categorie=CatCashless,
                                                   methode_choices=Articles.RECHARGE_EUROS,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle'))[0]

                d["+0.5"] = \
                    Articles.objects.get_or_create(name="+0.5",
                                                   prix=0.5,
                                                   categorie=CatCashless,
                                                   methode_choices=Articles.RECHARGE_EUROS,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle'))[0]

                d["+1"] = \
                    Articles.objects.get_or_create(name="+1",
                                                   prix=1,
                                                   categorie=CatCashless,
                                                   methode_choices=Articles.RECHARGE_EUROS,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle'))[0]

                d["+5"] = \
                    Articles.objects.get_or_create(name="+5",
                                                   prix=5,
                                                   categorie=CatCashless,
                                                   methode_choices=Articles.RECHARGE_EUROS,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle'))[0]

                d["+10"] = \
                    Articles.objects.get_or_create(name="+10",
                                                   prix=10,
                                                   categorie=CatCashless,
                                                   methode_choices=Articles.RECHARGE_EUROS,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle'))[0]

                d["+20"] = \
                    Articles.objects.get_or_create(name="+20",
                                                   prix=20,
                                                   categorie=CatCashless,
                                                   methode_choices=Articles.RECHARGE_EUROS,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle'))[0]

                # d["+1F"] = \
                #     Articles.objects.get_or_create(name="+1€ Fed",
                #                                    prix=1,
                #                                    methode_choices=Articles.RECHARGE_EUROS_FEDERE,
                #                                    )[0]

                d["Retour Consigne"] = \
                    Articles.objects.get_or_create(name="Retour Consigne",
                                                   prix=-1,
                                                   categorie=CatConsigne,
                                                   methode_choices=Articles.RETOUR_CONSIGNE,
                                                   methode=self.methode_articles.get(
                                                       'retour_consigne'))[0]



                d["Cadeau +0.1"] = \
                    Articles.objects.get_or_create(name="Cadeau +0.1",
                                                   prix=0.1,
                                                   categorie=CatCadeau,
                                                   methode_choices=Articles.RECHARGE_CADEAU,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle_cadeau'))[0]

                d["Cadeau +0.5"] = \
                    Articles.objects.get_or_create(name="Cadeau +0.5",
                                                   prix=0.5,
                                                   categorie=CatCadeau,
                                                   methode_choices=Articles.RECHARGE_CADEAU,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle_cadeau'))[0]

                d["Cadeau +1"] = \
                    Articles.objects.get_or_create(name="Cadeau +1",
                                                   prix=1,
                                                   categorie=CatCadeau,
                                                   methode_choices=Articles.RECHARGE_CADEAU,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle_cadeau'))[0]

                d["Cadeau +5"] = \
                    Articles.objects.get_or_create(name="Cadeau +5",
                                                   prix=5,
                                                   categorie=CatCadeau,
                                                   methode_choices=Articles.RECHARGE_CADEAU,
                                                   methode=self.methode_articles.get(
                                                       'ajout_monnaie_virtuelle_cadeau'))[0]

                # L'adhésion vient de Fedow maintenant
                # d["Adhésion"] = \
                #     Articles.objects.get_or_create(name="Adhésion",
                #                                    prix=10,
                #                                    methode_choices=Articles.ADHESIONS,
                #                                    methode=self.methode_articles.get('adhesion'))[0]

                d["VIDER CARTE"] = \
                    Articles.objects.get_or_create(name="VIDER CARTE",
                                                   categorie=CatDanger,
                                                   methode_choices=Articles.VIDER_CARTE,
                                                   methode=self.methode_articles.get('vider_carte'))[0]

                d["Paiement Fractionné"] = \
                    Articles.objects.get_or_create(name="Paiement Fractionné",
                                                   categorie=None,
                                                   fractionne=True,
                                                   prix=1,
                                                   prix_achat=1,
                                                   methode_choices=Articles.FRACTIONNE,
                                                   methode=self.methode_articles.get('paiement_fractionne'))[0]

                return d

            def _point_de_vente_cashless(self):
                cashless_pdv = PointDeVente.objects.create(
                    name="Cashless",
                    icon="fa-euro-sign",
                    comportement='C',
                    accepte_commandes=False,
                    service_direct=True,
                    poid_liste=200,
                )

                for key, art in self.articles_generiques.items():
                    cashless_pdv.articles.add(art) if art not in cashless_pdv.articles.all() else art

                return cashless_pdv

            def _couleur(self):
                couleurs = [
                    Couleur.objects.get_or_create(name='Aqua', name_fr="Aqua", hexa="#00FFFF"),
                    Couleur.objects.get_or_create(name='Black', name_fr="Noir", hexa="#000000"),
                    Couleur.objects.get_or_create(name='Blue', name_fr="Bleu", hexa="#337ab7"),
                    Couleur.objects.get_or_create(name='Fuchsia', name_fr="Fuchsia", hexa="#FF00FF"),
                    Couleur.objects.get_or_create(name='Gray', name_fr="Gris", hexa="#808080"),
                    Couleur.objects.get_or_create(name='Green', name_fr="Vert", hexa="#4caf50"),
                    Couleur.objects.get_or_create(name='Lime', name_fr="Citron", hexa="#00FF00"),
                    Couleur.objects.get_or_create(name='Maroon', name_fr="Marron", hexa="#800000"),
                    Couleur.objects.get_or_create(name='Navy', name_fr="Marine", hexa="#000080"),
                    Couleur.objects.get_or_create(name='Olive', name_fr="Olive", hexa="#808000"),
                    Couleur.objects.get_or_create(name='Purple', name_fr="Mauve", hexa="#800080"),
                    Couleur.objects.get_or_create(name='Red', name_fr="Rouge", hexa="#FF0000"),
                    Couleur.objects.get_or_create(name='Silver', name_fr="Argent", hexa="#C0C0C0"),
                    Couleur.objects.get_or_create(name='Teal', name_fr="Turquoise", hexa="#0e9aa7"),
                    Couleur.objects.get_or_create(name='White', name_fr="Blanc", hexa="#FFFFFF"),
                    Couleur.objects.get_or_create(name='Yellow', name_fr="Jaune", hexa="#f6cd61"),
                    Couleur.objects.get_or_create(name='Orange', name_fr="Orange", hexa="#E64A19"),

                ]
                return couleurs

            def _create_admin_from_env_email(self):
                # Création de l'user admin via l'email dans le .env
                User = get_user_model()
                staff_group, created = Group.objects.get_or_create(name="staff")
                email_first_admin = os.environ['ADMIN_EMAIL']
                admin, created = User.objects.get_or_create(
                    username=email_first_admin,
                    email=email_first_admin,
                    is_staff=True,
                    is_active=False,
                )
                admin.groups.add(staff_group)
                admin.save()
                try :
                    email_activation(admin.uuid)
                except :
                    logger.error("Email for admin activation FAILED")
                call_command('check_permissions')
                return admin

            def _lespass_handshake(self):
                # On ping LesPass
                config = Configuration.get_solo()
                lespass_url = self.lespass_url
                lespass_state = None
                ping_count = 0

                while not lespass_state:
                    # On récupère la clé publique de l'admin commun
                    hello_lespass = requests.post(f'{lespass_url}api/get_user_pub_pem/',
                                                  data={
                                                      "email": f"{os.environ['ADMIN_EMAIL']}",
                                                  },
                                                  verify=bool(not settings.DEBUG))
                    # Returns True if :attr:`status_code` is less than 400, False if not
                    if hello_lespass.ok:
                        lespass_state = hello_lespass.status_code
                        logger.info(f'ping lespass_url at {lespass_url} OK')
                    else:
                        ping_count += 1
                        logger.warning(
                            f'ping lespass_url at {lespass_url} without succes. sleep(1) : count {ping_count}')
                        sleep(1)

                # noinspection PyUnboundLocalVariable
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
                                                  },
                                                  verify=bool(not settings.DEBUG))

                # Le serveur LesPass renvoie la clé pour se connecter à Fedow, chiffrée avec une clé Fernet aléatoire
                # La clé fernet qui déchiffre le json :
                handshake_lespass_data =handshake_lespass.json()
                cypher_rand_key = handshake_lespass_data['cypher_rand_key']
                fernet_key = rsa_decrypt_string(utf8_enc_string=cypher_rand_key, private_key=config.get_private_key())
                cypher_json_key_to_cashless = handshake_lespass_data['cypher_json_key_to_cashless']

                decryptor = Fernet(fernet_key)
                config.string_connect = decryptor.decrypt(cypher_json_key_to_cashless.encode('utf-8')).decode('utf8')
                config.billetterie_url = self.lespass_url
                # Le nom de la structure est le même que le tenant

                config.structure = handshake_lespass_data.get('organisation_name')

                config.siret = handshake_lespass_data.get('siren')
                config.adresse = (f"{handshake_lespass_data.get('adress')} "
                                  f"{handshake_lespass_data.get('postal_code')} "
                                  f"{handshake_lespass_data.get('city')}")
                config.telephone = handshake_lespass_data.get('phone')
                config.numero_tva = handshake_lespass_data.get('tva_number')

                config.save()
                logger.info("Lespass Plugged !")

            def _fedow_handshake(self):
                # On ping Fedow
                config = Configuration.get_solo()

                fedow_url = self.fedow_url
                fedow_state = None
                ping_count = 0
                while not fedow_state:
                    hello_fedow = requests.get(f'{fedow_url}helloworld/',
                                               verify=bool(not settings.DEBUG))
                    # Returns True if :attr:`status_code` is less than 400, False if not
                    if hello_fedow.ok:
                        fedow_state = hello_fedow.status_code
                        logger.info(f'ping fedow at {fedow_url} OK')
                    else:
                        ping_count += 1
                        logger.warning(
                            f'ping fedow at {fedow_url}helloworld/ without succes. sleep(1) : count {ping_count}')
                        sleep(1)

                # Récupération de l'adresse IP du serveur Laboutik :
                # obligatoire pour le handshake fedow :
                if 'test' in sys.argv:
                    # MODE TEST
                    # On doit changer le nom de la structure
                    # sinon erreur de création coté Fedow
                    fake = Faker()
                    rand_uuid = str(uuid4())[:4]
                    config.structure = f"{config.structure} {rand_uuid}"
                    # On ajoute un random à TestCoin
                    self.main_asset = os.environ['MAIN_ASSET_NAME'] + f" {rand_uuid}"
                    config.email = fake.email()

                    # On est en mode test, on va chercher une clé de test pour le handshake
                    # En mode demo/dev, cela se fait par le flush.sh
                    # Récupération d'une clé de test sur Fedow :
                    name_enc = data_to_b64({'name': f'{config.structure}'})
                    url = f'{config.fedow_domain}get_new_place_token_for_test/{name_enc.decode("utf8")}/'
                    request = requests.get(url, verify=False, data={'name': f'{config.structure}'}, timeout=1)
                    if request.status_code != 200:
                        raise Exception("Erreur de connexion au serveur de test")

                    string_connect = request.json().get('encoded_data')
                    config.string_connect = string_connect
                    config.save()

                # Mode debug, l'ip est surement localhost
                if settings.DEBUG:
                    # Ip du serveur cashless et du ngnix dans le même réseau ( env de test )
                    self_ip = socket.gethostbyname(socket.gethostname())
                    templist: list = self_ip.split('.')
                    templist[-1] = 1
                    config.ip_cashless = '.'.join([str(ip) for ip in templist])
                    config.billetterie_ip_white_list = '.'.join([str(ip) for ip in templist])

                else:
                    config.ip_cashless = requests.get('https://ipinfo.io/ip').content.decode('utf8')

                # Lancement du handshake
                # first_handshake lance des fonctions celery pour envoyer les assets
                decoded_data = jsonb64decode(config.string_connect)
                if decoded_data['domain'] not in fedow_url:
                    raise Exception('Bad Fedow domain. Check env file on both system.')

                # Validé et vérifié, on entre l'RUL -> avec https://fedow.tibillet.localhost/
                config.fedow_domain = fedow_url
                config.save()

                if handshake(config):
                    after_handshake()

                config.refresh_from_db()
                if not config.can_fedow():
                    logger.error(
                        'Error handhsake Fedow. Please double check all you environnement and relaunch from scratch '
                        '(./flush.sh on Fedow, after Lespass and after LaBoutik)')
                    raise Exception(
                        'Error handhsake Fedow. Please double check all you environnement and relaunch from scratch '
                        '(./flush.sh on Fedow, after Lespass and after LaBoutik)')

                logger.info(f'Fedow handhshake OK !!!!!!!!!!!!')

            ### DEMO AND TEST DATA ###
            def set_admin_user_active(self):
                self.admin.is_active = True
                self.admin.save()

            def pop_membre_articles_cartes_test(self):
                testMembre, created = Membre.objects.get_or_create(name="TEST")
                jonas_membre, created = Membre.objects.get_or_create(name="JONAS")
                robocop_membre, created = Membre.objects.get_or_create(name="ROBOCOP")
                framboise_membre, created = Membre.objects.get_or_create(name="FRAMBOISIÉ")
                origin = Origin.objects.get_or_create(generation=1)[0]

                cards = []
                if 'test' in sys.argv:
                    for i in range(10):
                        fake_uuid = str(uuid4()).upper()
                        cards.append(
                            [f"https://demo.tibillet.localhost/qr/{fake_uuid}", fake_uuid[:8],
                             str(uuid4())[:8].upper()]
                        )
                # pour cashless demo 1
                elif os.environ.get('MAIN_ASSET_NAME') == 'TestCoin':
                    cards = [
                        ["https://demo.tibillet.localhost/qr/76dc433c-00ac-479c-93c4-b7a0710246af", "76DC433C",
                         "EE144CE8"],
                        ["https://demo.tibillet.localhost/qr/87683c94-1187-49ae-a64d-54174f6eb76d", "87683C94",
                         "93BD3684"],
                        ["https://demo.tibillet.localhost/qr/c2b2400c-1f7e-4305-b75e-8c1db3f8d113", "C2B2400C",
                         "41726643"],
                        ["https://demo.tibillet.localhost/qr/7c9b0d8a-6c37-433b-a091-2c6017b085f0", "7C9B0D8A",
                         "11372ACA"],
                        ["https://demo.tibillet.localhost/qr/8ee38b17-fc02-4c8d-84cb-59eaaa059ee0", "A9253967",
                         "4D64463B"],
                        ["https://demo.tibillet.localhost/qr/f75234fc-0c86-40cf-ae00-604cd3719403", "F75234FC",
                         "CC3EB41E"],
                        ["https://demo.tibillet.localhost/qr/b2eba074-f070-4fe3-9150-deda224b708d", "B2EBA074",
                         "91168FE9"],
                        ["https://demo.tibillet.localhost/qr/5ddb4c9f-5f9e-4fa1-aacb-60316f2a3aea", "5DDB4C9F",
                         "A14F75E9"],
                        ["https://demo.tibillet.localhost/qr/189ce45e-d606-4e5a-bfbe-5ed5ec5e4995", "189CE45E",
                         "A14DD6CA"],
                        ["https://demo.tibillet.localhost/qr/d6cad253-b6cf-4d8f-9238-0927de8a4ce9", "D6CAD253",
                         "01F097CA"],
                        ["https://demo.tibillet.localhost/qr/eced8aef-3e1f-4614-be11-b756768c9bad", "ECED8AEF",
                         "4172AACA"],
                        ["https://demo.tibillet.localhost/qr/7dc2fee6-a312-4ff3-849c-b26da9302174", "7DC2FEE6",
                         "F18923CB"],
                        ["https://m.tibillet.re/qr/ff71becc-c75c-47bc-9b1e-08cf71aa3eb6", "FF71BECC", "3D30DC3F"],
                        ["https://m.tibillet.re/qr/91cbf50a-e7af-4b03-9c03-a65e5475d31b", "91CBF50A", "2DEB7B40"],
                        ["https://m.tibillet.re/qr/c3db3821-bc6a-487b-926d-36b6ff943994", "C3DB3821", "AD1E7E40"],
                        ["https://m.tibillet.re/qr/0c9e2d94-0628-45df-b30d-c974ee4cc3e4", "0C9E2D94", "9DD67D40"],
                        ["https://m.tibillet.re/qr/b1346b95-9a25-42dc-9067-e7a9f3d03d47", "B1346B95", "2DF5A23B"],
                        ["https://m.tibillet.re/qr/7eef8be2-d605-4f61-a11a-00e94dfc7953", "7EEF8BE2", "7D568D3B"],
                        ["https://m.tibillet.re/qr/2182d39f-74e5-490f-a2dd-c57ef2e2e002", "2182D39F", "BD2FAF3F"],
                        ["https://m.tibillet.re/qr/d70fe430-439d-4ca5-a3ab-58fa21cac23e", "D70FE430", "BD8A0F40"],
                        ["https://m.tibillet.re/qr/312d83fd-bf04-4712-a082-0671b59c91c2", "312D83FD", "1D51AE3F"],
                        ["https://m.tibillet.re/qr/147701d4-747b-4934-93f2-597449bcde22", "147701D4", "BDCE2140"],
                        ["https://m.tibillet.re/qr/58515F52-747b-4934-93f2-597449bcde22", "58515F52", "52BE6543"],
                    ]
                else:
                    # Pour cashless_test2
                    cards = [
                        ["https://demo.tibillet.localhost/qr/81fd9485-c806-4991-adf8-6cb44ee5e6d1", "81FD9485",
                         "6172BACA"],
                        ["https://demo.tibillet.localhost/qr/a84133d3-7855-4cb9-ae2c-f54dee027301", "A84133D3",
                         "F3892ACB"],
                        ["https://billetistan.tibillet.localhost/qr/86dc433c-00ac-479c-93c4-b7a0710246af",
                         "86DC433C",
                         "8E144CE8"],
                    ]
                    for i in range(100):
                        fake_uuid = str(uuid4()).upper()
                        cards.append(
                            [f"https://billetistan.tibillet.localhost/qr/{fake_uuid}", fake_uuid[:8],
                             str(uuid4())[:8].upper()]
                        )

                cards_db = []
                for card in cards:
                    part = card[0].partition('/qr/')
                    uuid_url = UUID(part[2])
                    logger.info("Create card : ")
                    logger.info(card)
                    CC, created = CarteCashless.objects.get_or_create(
                        number=card[1],
                        tag_id=card[2],
                        uuid_qrcode=uuid_url,
                        origin=origin,
                    )
                    cards_db.append(CC)

                cards_db[0].membre = testMembre
                cards_db[0].save()
                cards_db[2].membre = robocop_membre
                cards_db[2].save()
                cards_db[3].membre = jonas_membre
                cards_db[3].save()
                cards_db[4].membre = framboise_membre
                cards_db[4].save()

                bar1, created = PointDeVente.objects.get_or_create(
                    name="Bar 1",
                    poid_liste=1,
                    icon='fa-beer',
                )
                Resto, created = PointDeVente.objects.get_or_create(
                    name="Resto",
                    service_direct=False,
                    poid_liste=2,
                    icon='fa-hamburger',
                )
                Boutique, created = PointDeVente.objects.get_or_create(name="Boutique", poid_liste=4)
                test = PointDeVente.objects.get_or_create(name="Test", poid_liste=5)[0]

                carteM, created = CarteMaitresse.objects.get_or_create(carte=cards_db[0], edit_mode=True)
                carteM.points_de_vente.add(Resto)
                carteM.points_de_vente.add(bar1)
                carteM.points_de_vente.add(test)
                carteM.points_de_vente.add(self.pdv_cashless)

                carteM3, created = CarteMaitresse.objects.get_or_create(carte=cards_db[2], edit_mode=True)
                carteM3.points_de_vente.add(Resto)
                carteM3.points_de_vente.add(bar1)
                carteM3.points_de_vente.add(Boutique)
                carteM3.points_de_vente.add(self.pdv_cashless)

                carteM4, created = CarteMaitresse.objects.get_or_create(carte=cards_db[3], edit_mode=True)
                carteM4.points_de_vente.add(Resto)
                carteM4.points_de_vente.add(bar1)
                carteM4.points_de_vente.add(Boutique)
                carteM4.points_de_vente.add(self.pdv_cashless)

                carteM5, created = CarteMaitresse.objects.get_or_create(carte=cards_db[4], edit_mode=True)
                carteM5.points_de_vente.add(Resto)
                carteM5.points_de_vente.add(bar1)
                carteM5.points_de_vente.add(Boutique)
                carteM5.points_de_vente.add(self.pdv_cashless)


                ### FIN DE CREATION DE CARTES

                if os.environ.get('MAIN_ASSET_NAME') == 'Bilstou':
                    # On mets des valeurs d'assets au pif pour le cashless2
                    mp_primary = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
                    mp_gift = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)

                    for card in CarteCashless.objects.all():
                        asset_primary = Assets.objects.create(
                            qty=random.randint(0, 100),
                            carte=card,
                            monnaie=mp_primary,
                        )
                        asset_gift = Assets.objects.create(
                            qty=random.randint(0, 100),
                            carte=card,
                            monnaie=mp_gift,
                        )

            def pop_articles_test(self):

                articles = []

                articles.append(self.articles_generiques.get('Retour Consigne'))

                vente_article = self.configuration.methode_vente_article

                tva20 = TauxTVA.objects.get_or_create(taux=20, name="Alcool")[0]
                tva10 = TauxTVA.objects.get_or_create(taux=10, name="Restauration")[0]
                tva85 = TauxTVA.objects.get_or_create(taux=8.5, name="Run Alcool")[0]
                tva21 = TauxTVA.objects.get_or_create(taux=2.1, name="Run Resto")[0]

                CatSoft, created = Categorie.objects.get_or_create(name="Soft",
                                                                   couleur_backgr=Couleur.objects.get(name='Blue'),
                                                                   icon='fa-coffee',
                                                                   tva=tva10)

                CatPression, created = Categorie.objects.get_or_create(name="Pression",
                                                                       couleur_backgr=Couleur.objects.get(
                                                                           name='Yellow'),
                                                                       icon='fa-beer',
                                                                       tva=tva20)

                CatBierre, created = Categorie.objects.get_or_create(name="Bieres Btl",
                                                                     couleur_backgr=Couleur.objects.get(
                                                                         name='Lime'),
                                                                     icon='fa-wine-bottle',
                                                                     tva=tva20)

                CatMenu, created = Categorie.objects.get_or_create(name="Menu",
                                                                   couleur_backgr=Couleur.objects.get(name='Red'),
                                                                   icon='fa-hamburger',
                                                                   tva=tva85)

                CatDessert, created = Categorie.objects.get_or_create(name="Dessert",
                                                                      couleur_backgr=Couleur.objects.get(
                                                                          name='Orange'),
                                                                      icon='fa-birthday-cake',
                                                                      tva=tva21)

                articles.append(
                    Articles.objects.get_or_create(name="Pression 33", prix=2, methode_choices=Articles.VENTE,
                                                   methode=vente_article, categorie=CatPression)[0])
                articles.append(
                    Articles.objects.get_or_create(name="Pression 50", prix=2.5, methode_choices=Articles.VENTE,
                                                   methode=vente_article, categorie=CatPression)[0])
                articles.append(Articles.objects.get_or_create(name="Eau 50cL", prix=1, prix_achat=0.5,
                                                               methode_choices=Articles.VENTE,
                                                               methode=vente_article, categorie=CatSoft)[0])
                articles.append(Articles.objects.get_or_create(name="Eau 1L", prix=1.5, prix_achat=0.75,
                                                               methode_choices=Articles.VENTE,
                                                               methode=vente_article, categorie=CatSoft)[0])
                articles.append(
                    Articles.objects.get_or_create(name="Café", prix=1, prix_achat=0.5,
                                                   methode_choices=Articles.VENTE,
                                                   methode=vente_article, categorie=CatSoft)[0])
                articles.append(Articles.objects.get_or_create(name="Soft P", prix=1, prix_achat=0.5,
                                                               methode_choices=Articles.VENTE,
                                                               methode=vente_article, categorie=CatSoft)[0])
                articles.append(Articles.objects.get_or_create(name="Soft G", prix=1.5, prix_achat=0.8,
                                                               methode_choices=Articles.VENTE,
                                                               methode=vente_article, categorie=CatSoft)[0])
                articles.append(
                    Articles.objects.get_or_create(name="Guinness", prix=4.99, prix_achat=3,
                                                   methode_choices=Articles.VENTE,
                                                   methode=vente_article, categorie=CatBierre)[0])
                articles.append(
                    Articles.objects.get_or_create(name="Despé", prix=3.2, prix_achat=2.1,
                                                   methode_choices=Articles.VENTE,
                                                   methode=vente_article, categorie=CatBierre)[0])
                articles.append(
                    Articles.objects.get_or_create(name="Chimay Bleue", prix=2.8, prix_achat=1.4,
                                                   methode_choices=Articles.VENTE,
                                                   methode=vente_article,
                                                   categorie=CatBierre)[0])
                articles.append(
                    Articles.objects.get_or_create(name="Chimay Rouge", prix=2.6, prix_achat=1.3,
                                                   methode_choices=Articles.VENTE,
                                                   methode=vente_article,
                                                   categorie=CatBierre)[0])

                articles.append(Articles.objects.get_or_create(name="CdBoeuf", prix=25, prix_achat=12,
                                                               methode_choices=Articles.VENTE,
                                                               methode=vente_article, categorie=CatMenu)[0])
                articles.append(
                    Articles.objects.get_or_create(name="Gateau", prix=8, methode_choices=Articles.VENTE,
                                                   methode=vente_article, categorie=CatDessert)[0])

                Resto = PointDeVente.objects.get(name="Resto")
                bar1 = PointDeVente.objects.get(name="Bar 1")

                ## LE PDV TEST POUR NICO
                test = PointDeVente.objects.get(name="Test")
                test.articles.add(Articles.objects.get_or_create(name="Retour Consigne bis",
                                                   prix=-1,
                                                   methode_choices=Articles.RETOUR_CONSIGNE)[0])

                test.articles.add(Articles.objects.get_or_create(name="Retour Consigne Rebis",
                                                                 prix=-1,
                                                                 methode_choices=Articles.RETOUR_CONSIGNE)[0])

                for art in articles:
                    bar1.articles.add(art) if art not in bar1.articles.all() else art

                for art in articles:
                    Resto.articles.add(art) if art not in Resto.articles.all() else art

                return True

            def pop_tables_test(self):
                Table.objects.get_or_create(name="S01")
                Table.objects.get_or_create(name="S02")
                Table.objects.get_or_create(name="S03")
                Table.objects.get_or_create(name="S04")
                Table.objects.get_or_create(name="S05")
                Table.objects.get_or_create(name="Ex01")
                Table.objects.get_or_create(name="Ex02")
                Table.objects.get_or_create(name="Ex03")
                Table.objects.get_or_create(name="Ex04")
                Table.objects.get_or_create(name="Ex05")

            def preparation_test(self):
                prepa_cuisine, created = GroupementCategorie.objects.get_or_create(name="CUISINE")
                prepa_tireuse, created = GroupementCategorie.objects.get_or_create(name="TIREUSE")

                CatSoft = Categorie.objects.get(name="Soft")
                CatPression = Categorie.objects.get(name="Pression")
                CatBierre = Categorie.objects.get(name="Bieres Btl")
                CatMenu = Categorie.objects.get(name="Menu")
                CatDessert = Categorie.objects.get(name="Dessert")

                prepa_tireuse.categories.add(CatSoft)
                prepa_tireuse.categories.add(CatPression)
                prepa_tireuse.categories.add(CatBierre)
                prepa_cuisine.categories.add(CatMenu)
                prepa_cuisine.categories.add(CatDessert)

            def printer_test(self):

                PRINT_SERVEUR = os.environ.get('PRINT_SERVEUR')
                PRINT_SERVEUR_APIKEY = os.environ.get('PRINT_SERVEUR_APIKEY')
                if PRINT_SERVEUR and PRINT_SERVEUR_APIKEY:
                    PRINTER_1_NAME = os.environ.get('PRINTER_1_NAME')
                    PRINTER_1_IP = os.environ.get('PRINTER_1_IP')
                    PRINTER_2_NAME = os.environ.get('PRINTER_2_NAME')
                    PRINTER_2_IP = os.environ.get('PRINTER_2_IP')

                    if PRINTER_1_NAME and PRINTER_1_IP:
                        tm20, created = Printer.objects.get_or_create(
                            name=PRINTER_1_NAME,
                            thermal_printer_adress=PRINTER_1_IP,
                            serveur_impression=PRINT_SERVEUR,
                            api_serveur_impression=PRINT_SERVEUR_APIKEY
                        )
                        prepa_cuisine = GroupementCategorie.objects.get(name="CUISINE")
                        prepa_cuisine.printer = tm20
                        prepa_cuisine.save()

                    if PRINTER_2_NAME and PRINTER_2_IP:
                        tm30, created = Printer.objects.get_or_create(
                            name=PRINTER_2_NAME,
                            thermal_printer_adress=PRINTER_2_IP,
                            serveur_impression=PRINT_SERVEUR,
                            api_serveur_impression=PRINT_SERVEUR_APIKEY
                        )

                        prepa_tireuse = GroupementCategorie.objects.get(name="TIREUSE")
                        prepa_tireuse.printer = tm30
                        prepa_tireuse.save()

                    return True
                return False


            def add_membership_and_badge_articles(self):
                # On est dans un environnement de test/dev/debug,
                # on rajoute ces articles dans un point de vente et dans toutes les cartes primaires.
                # Ces adhésion et badge ont été créé par le serializer ProductFromLespassValidator
                pdv_adh, created = PointDeVente.objects.get_or_create(
                    name="Adhésions",
                )

                adhesions_badges = Articles.objects.filter(
                    methode_choices__in=[Articles.ADHESIONS, Articles.BADGEUSE]
                )

                for price in adhesions_badges:
                    pdv_adh.articles.add(price)
                for carte in CarteMaitresse.objects.all():
                    carte.points_de_vente.add(pdv_adh)



        ### RUNER ###
        if PointDeVente.objects.count() > 0:
            logger.warning(f'PointDeVente.objects.count() > 0. Pop déja effectué')
        else:
            Install(options)
