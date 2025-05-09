#!/usr/bin/env python3
import os
import sys
import socket
import logging
from time import sleep
from uuid import UUID, uuid4

import requests
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from django.conf import settings
from django.core.cache import cache

from APIcashless.custom_utils import jsonb64decode
from APIcashless.models import *
from APIcashless.tasks import email_activation
from fedow_connect.tasks import after_handshake
from fedow_connect.utils import get_public_key, rsa_encrypt_string, rsa_decrypt_string, data_to_b64
from fedow_connect.views import handshake

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Install TiBillet/LaBoutik with fixtures'

    def add_arguments(self, parser):
        parser.add_argument('--tdd',
                            action='store_true',
                            help='Demo data for Test driven dev')
        parser.add_argument('--skip-handshake',
                            action='store_true',
                            help='Skip Fedow and LesPass handshake (for testing)')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting TiBillet/LaBoutik installation with fixtures'))
        
        # Load the appropriate fixture
        if options.get('tdd'):
            self.stdout.write(self.style.SUCCESS('Loading test fixture...'))
            call_command('loaddata', 'test_fixture.json')
        else:
            self.stdout.write(self.style.SUCCESS('Loading production fixture...'))
            call_command('loaddata', 'prod_fixture.json')
        
        # Initialize the installer
        installer = Installer(options)
        
        # Run tests to verify installation
        self.run_tests(installer)
        
        self.stdout.write(self.style.SUCCESS('Installation completed successfully!'))
    
    def run_tests(self, installer):
        """Run tests to verify the installation was successful"""
        self.stdout.write(self.style.SUCCESS('Running tests to verify installation...'))
        
        # Test 1: Check if Configuration exists
        try:
            config = Configuration.get_solo()
            self.stdout.write(self.style.SUCCESS('✓ Configuration exists'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Configuration does not exist: {e}'))
            return False
        
        # Test 2: Check if MoyenPaiement objects exist
        try:
            moyens_paiement = MoyenPaiement.objects.all()
            if moyens_paiement.count() >= 7:
                self.stdout.write(self.style.SUCCESS(f'✓ MoyenPaiement objects exist ({moyens_paiement.count()})'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ Only {moyens_paiement.count()} MoyenPaiement objects exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error checking MoyenPaiement objects: {e}'))
            return False
        
        # Test 3: Check if Methode objects exist
        try:
            methodes = Methode.objects.all()
            if methodes.count() >= 6:
                self.stdout.write(self.style.SUCCESS(f'✓ Methode objects exist ({methodes.count()})'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ Only {methodes.count()} Methode objects exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error checking Methode objects: {e}'))
            return False
        
        # Test 4: Check if Couleur objects exist
        try:
            couleurs = Couleur.objects.all()
            if couleurs.count() >= 17:
                self.stdout.write(self.style.SUCCESS(f'✓ Couleur objects exist ({couleurs.count()})'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ Only {couleurs.count()} Couleur objects exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error checking Couleur objects: {e}'))
            return False
        
        # Test 5: Check if Categorie objects exist
        try:
            categories = Categorie.objects.all()
            if categories.count() >= 5:
                self.stdout.write(self.style.SUCCESS(f'✓ Categorie objects exist ({categories.count()})'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ Only {categories.count()} Categorie objects exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error checking Categorie objects: {e}'))
            return False
        
        # Test 6: Check if admin user exists
        try:
            User = get_user_model()
            admin_email = os.environ['ADMIN_EMAIL']
            admin = User.objects.filter(email=admin_email).first()
            if admin:
                self.stdout.write(self.style.SUCCESS(f'✓ Admin user exists ({admin_email})'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ Admin user does not exist ({admin_email})'))
                return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error checking admin user: {e}'))
            return False
        
        # Test 7: Check if PointDeVente objects exist
        try:
            points_de_vente = PointDeVente.objects.all()
            if points_de_vente.count() >= 3:
                self.stdout.write(self.style.SUCCESS(f'✓ PointDeVente objects exist ({points_de_vente.count()})'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ Only {points_de_vente.count()} PointDeVente objects exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error checking PointDeVente objects: {e}'))
            return False
        
        # All tests passed
        self.stdout.write(self.style.SUCCESS('All tests passed!'))
        return True


class Installer:
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
        # Au format https://fedow.tibillet.localhost/
        if not self.lespass_url.endswith("/"):
            self.lespass_url += "/"
        if not self.lespass_url.startswith("https://"):
            raise Exception("Lespass URL must start with https://")
        
        # Update configuration with values from .env
        self.update_configuration()
        
        # Perform handshakes if not skipped
        if not options.get('skip_handshake'):
            self.lespass_handshake = self._lespass_handshake()
            self.fedow_handshake = self._fedow_handshake()
        
        # Update asset names from .env
        self.update_assets()
        
        # Create admin user
        self.admin = self._create_admin_from_env_email()
        
        # Additional setup for test mode
        if options.get('tdd'):
            self.set_admin_user_active()
    
    def update_configuration(self):
        """Update configuration with values from .env"""
        config = Configuration.get_solo()
        config.email = os.environ['ADMIN_EMAIL']
        config.billetterie_url = os.environ['LESPASS_TENANT_URL']
        config.fedow_domain = os.environ['FEDOW_URL']
        config.domaine_cashless = os.environ.get('DOMAIN', '')
        
        # Debug mode settings
        if os.environ.get('DEBUG') == '1':
            config.validation_service_ecran = True
            config.remboursement_auto_annulation = True
            
            # Ip du serveur cashless et du ngnix dans le même réseau (env de test)
            self_ip = socket.gethostbyname(socket.gethostname())
            templist: list = self_ip.split('.')
            templist[-1] = 1
            config.ip_cashless = '.'.join([str(ip) for ip in templist])
            config.billetterie_ip_white_list = '.'.join([str(ip) for ip in templist])
        
        config.save()
        logger.info("Configuration updated from .env")
        return config
    
    def update_assets(self):
        """Update asset names from .env"""
        # Update main asset name
        main_asset = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        main_asset.name = self.main_asset
        main_asset.save()
        
        # Update gift asset name
        gift_asset = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)
        gift_asset.name = f"{self.main_asset} Cadeau"
        gift_asset.save()
        
        logger.info(f"Asset names updated: {self.main_asset}, {gift_asset.name}")
    
    def _create_admin_from_env_email(self):
        """Create admin user from .env email"""
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
        try:
            email_activation(admin.uuid)
        except:
            logger.error("Email for admin activation FAILED")
        call_command('check_permissions')
        return admin
    
    def set_admin_user_active(self):
        """Set admin user as active (for test mode)"""
        self.admin.is_active = True
        self.admin.save()
        logger.info(f"Admin user {self.admin.email} set as active")
    
    def _lespass_handshake(self):
        """Perform handshake with LesPass"""
        # On ping LesPass
        config = Configuration.get_solo()
        lespass_url = os.environ['LESPASS_TENANT_URL']
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
                    f'ping lespass_url at {lespass_url} without success. sleep(1) : count {ping_count}')
                sleep(1)
        
        # noinspection PyUnboundLocalVariable
        lespass_admin_pub_pem = hello_lespass.json()['public_pem']
        lespass_admin_public_key = get_public_key(lespass_admin_pub_pem)
        
        # Pour les ancienne instances
        # APIKey.objects.filter(name="billetterie_key").delete()
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
        
        config.save()
        logger.info("Lespass Plugged !")
    
    def _fedow_handshake(self):
        """Perform handshake with Fedow"""
        # On ping Fedow
        config = Configuration.get_solo()
        fedow_url = os.environ['FEDOW_URL']
        
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
            from faker import Faker
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
        
        fedow_handshake = handshake(config)
        if fedow_handshake:
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