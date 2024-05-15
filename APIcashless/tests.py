import socket
from io import StringIO
from uuid import UUID

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.test import TestCase, tag
from faker import Faker

from APIcashless.custom_utils import badgeuse_creation, jsonb64decode
from APIcashless.models import *
from fedow_connect.fedow_api import FedowAPI
from fedow_connect.utils import data_to_b64
from fedow_connect.validators import TransactionValidator, AssetValidator
from fedow_connect.views import handshake


class TiBilletTestCase(TestCase):

    def setUp(self):
        settings.DEBUG = True
        call_command('install', stdout=StringIO())
        # Handshake avec le serveur FEDOW
        self.config = self.create_config()

    def create_config(self, string_fedow_connect=None):
        fake = Faker()
        config = Configuration.get_solo()
        config.structure = f"TEST {str(uuid4())[:4]}"
        config.siret = "666R999"
        config.adresse = fake.address()
        config.pied_ticket = "Nar'trouv vite' !"
        config.telephone = "+336123456789"
        config.domaine_cashless = "https://cashless.tibillet.localhost/"
        config.email = fake.email()
        config.numero_tva = 666999
        config.prix_adhesion = 42
        config.appareillement = True
        config.validation_service_ecran = True
        config.remboursement_auto_annulation = True
        config.string_connect = string_fedow_connect

        config.billetterie_url = 'https://demo.tibillet.localhost/'
        config.fedow_domain = 'https://fedow.tibillet.localhost/'

        # Ip du serveur cashless et du ngnix dans le même réseau ( env de test )
        self_ip = socket.gethostbyname(socket.gethostname())
        templist: list = self_ip.split('.')
        templist[-1] = 1
        config.ip_cashless = '.'.join([str(ip) for ip in templist])
        config.billetterie_ip_white_list = '.'.join([str(ip) for ip in templist])

        # Parfois l'ip prise est le 192...
        config.ip_cashless = "172.21.0.1"
        config.billetterie_ip_white_list = "172.21.0.1"
        
        config.save()
        return config


class CashlessTest(TiBilletTestCase):

    def handshake_with_fedow_serveur(self):
        # Réclamation d'une connexion a Fedow
        # session = requests.Session()
        # url = 'https://fedow.tibillet.localhost/get_new_place_token_for_test/'
        # request = session.get(url, verify=False, timeout=1)
        # string_fedow_connect = request.json().get('encoded_data')

        # Création de la config pour test
        config: Configuration = self.config
        self.fedowAPI = FedowAPI()
        settings.DEBUG = True

        # Récupération d'une clé de test sur Fedow :
        session = requests.Session()
        name_enc = data_to_b64({'name': f'{config.structure}'})
        url = f'{config.fedow_domain}get_new_place_token_for_test/{name_enc.decode("utf8")}/'


        request = session.get(url, verify=False, data={'name': f'{config.structure}'}, timeout=1)
        if request.status_code != 200:
            raise Exception("Erreur de connexion au serveur de test")

        string_connect = request.json().get('encoded_data')
        config.string_connect = string_connect
        config.save()

        # Handshake avec le serveur FEDOW
        handshake_with_fedow = handshake(config)
        if not handshake_with_fedow:
            raise Exception("Erreur de handshake")

        # Ajout des infos reçu par le handshake dans la config
        config.fedow_place_admin_apikey = handshake_with_fedow.get('place_admin_apikey')
        config.fedow_place_uuid = handshake_with_fedow.get('fedow_place_uuid')
        config.fedow_place_wallet_uuid = handshake_with_fedow.get('fedow_place_wallet_uuid')
        config.onboard_url = handshake_with_fedow.get('url_onboard')
        config.fedow_domain = handshake_with_fedow.get('fedow_domain')

        # On simule la synchro
        config.fedow_synced = True

        config.save()

        self.fedowAPI = FedowAPI()
        if not config.can_fedow():
            import ipdb; ipdb.set_trace()
        self.assertTrue(config.can_fedow())
        return config

    def connect_admin(self):
        User = get_user_model()
        settings.DEBUG = False
        self.client.logout()

        # Anonymous
        response = self.client.get('/adminroot', follow=True)
        self.assertEqual(response.status_code, 404)
        # self.assertRedirects(response, '/adminroot/login/?next=/adminstaff/', status_code=301, target_status_code=200)

        response = self.client.get('/adminstaff', follow=True)
        self.assertRedirects(response, '/adminstaff/login/?next=/adminstaff/', status_code=301, target_status_code=200)

        response = self.client.get('/wv', follow=True)
        self.assertRedirects(response, '/wv/login_hardware?next=/wv/', status_code=301, target_status_code=200)

        # Retourne vers l'url de login
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertInHTML('<input name="username" id="username" type="text" placeholder="username"/>', response.content.decode())
        self.assertInHTML('<input name="password" id="password" type="password" placeholder="password"/>', response.content.decode())

        # User ROOT
        rootuser = User.objects.create_superuser('rootuser', 'root@root.root', 'ROOTUSERPASSWORD')
        log = self.client.login(username='rootuser', password='ROOTUSERPASSWORD')
        self.assertTrue(log)

        # Le root est desomais redirigé vers adminstaff
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 200)
        # On est loggué sur la page adminstaff/ avec un code 200 :
        self.assertRedirects(response, '/adminstaff/', status_code=302, target_status_code=200)

        response = self.client.get('/adminstaff', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, '/adminstaff/', status_code=301, target_status_code=200)

        # User Staff
        testadmin = User.objects.create(username='testadmin', is_staff=True, is_active=True)
        testadmin.set_password('TESTADMINPASSWORD')
        testadmin.save()
        log_admin = self.client.login(username='testadmin', password='TESTADMINPASSWORD')
        self.assertTrue(log_admin)

        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, '/adminstaff/', status_code=302, target_status_code=200)

        response = self.client.get('/adminroot', follow=True)
        self.assertEqual(response.status_code, 404)
        # self.assertRedirects(response, '/adminroot/login/?next=/adminroot/', status_code=301, target_status_code=200)

        # Log automatiquement sur un admin staff en mode DEBUG
        self.client.logout()
        settings.DEBUG = True
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 200)
        # 302 est la redirection une fois loggé, si t'es pas loggué, c'est un 301
        self.assertRedirects(response, '/adminstaff/login/?next=/adminstaff/', status_code=302, target_status_code=200)

        # Test avec un user lié à un appareil
        settings.DEBUG = False
        self.client.logout()
        appareil = Appareil.objects.create(name='testappareil')
        # On le met volontairement en staff pour tester que ça ne lui permette pas d'aller dans l'admin
        user_terminal = User.objects.create(
            username='user_terminal',
            is_active=True,
            is_staff=True,
        )
        user_terminal.set_password('PASSWORDTERMINAL')
        user_terminal.save()

        appareil.user = user_terminal
        appareil.save()

        user_terminal.refresh_from_db()
        self.assertEqual(user_terminal.appareil, appareil)

        appareil.refresh_from_db()
        self.assertEqual(appareil.user, user_terminal)

        log_user_terminal = self.client.login(username='user_terminal', password='PASSWORDTERMINAL')
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 405)

        return True

    def create_pos(self):
        boutique, created = PointDeVente.objects.get_or_create(name="Boutique", poid_liste=4)
        return boutique

    def create_cards_with_db(self):

        for i in range(20):
            fake_uuid = str(uuid4()).upper()
            carte_p = CarteCashless.objects.create(
                tag_id=f"{str(uuid4())[:8].upper()}",
                number=f"{fake_uuid[:8]}",
                uuid_qrcode=f"{fake_uuid}",
            )
            # Pour les 5 premières : carte primaire
            if i < 5:
                CarteMaitresse.objects.create(carte=carte_p)

        self.assertEqual(CarteMaitresse.objects.filter(
            points_de_vente__isnull=True,
            carte__isnull=False).count(), 5)

    def create_members_with_db(self):
        fake = Faker()

        # Utilisateurs avec cartes
        cartes = CarteCashless.objects.all()
        for i in range(5):
            date = fake.date_this_year()
            membre = Membre.objects.create(
                prenom=fake.first_name(),
                name=fake.last_name(),
                email=fake.email(),
                date_inscription=date,
                date_derniere_cotisation=date,
                cotisation=42,
            )
            carte = cartes.filter(cartes_maitresses__isnull=True)[i]
            carte.membre = membre
            carte.save()

        # Utilisateurs avec cartes primaire
        cartes = CarteCashless.objects.all()
        for i in range(5):
            date = fake.date_this_year()
            membre = Membre.objects.create(
                prenom=fake.first_name(),
                name=fake.last_name(),
                email=fake.email(),
                date_inscription=date,
                date_derniere_cotisation=date,
                cotisation=42,
            )
            carte = cartes.filter(cartes_maitresses__isnull=False)[i]
            carte.membre = membre
            carte.save()

        # Utilisateurs sans cartes ni adhésions
        for i in range(10):
            Membre.objects.create(
                prenom=fake.first_name(),
                name=fake.last_name(),
                email=fake.email(),
            )

        return Membre.objects.filter(CarteCashless_Membre__isnull=False).first()

    def link_card_primary_to_pos(self):
        boutique = PointDeVente.objects.get(name="Boutique")
        # boutique, created = PointDeVente.objects.get_or_create(name="Boutique")

        carte_m: CarteMaitresse = CarteMaitresse.objects.filter(
            points_de_vente__isnull=True,
            carte__membre__isnull=False).first()
        carte_m.points_de_vente.add(boutique)

        self.assertEqual(CarteMaitresse.objects.filter(
            points_de_vente__isnull=False,
            carte__isnull=False).count(), 1)

        self.assertEqual(PointDeVente.objects.filter(
            cartes_maitresses__isnull=False).count(), 1)

        return carte_m

    def paiement_espece_carte_bancaire(self):

        boisson: Articles = Articles.objects.create(
            name="Boisson_Test",
            prix=10,
            prix_achat="1",
            methode_choices=Articles.VENTE,
        )

        primary_card: CarteMaitresse = self.primary_card
        self.assertIsInstance(primary_card, CarteMaitresse)
        self.assertIsInstance(primary_card.carte, CarteCashless)
        responsable: Membre = primary_card.carte.membre
        self.assertIsInstance(responsable, Membre)

        pdv: PointDeVente = self.pos_boutique
        self.assertIsInstance(pdv, PointDeVente)

        # Paiement en espèce :
        qty = 3
        total: Decimal = dround((boisson.prix * qty))
        self.assertIsInstance(total, Decimal)
        json_achats = {"articles": [{"pk": f"{boisson.pk}", "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": total,
                       "moyen_paiement": 'espece',
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('route'), f"transaction_espece")
        self.assertEqual(response.json().get('somme_totale'), f"{total}")
        art_v: ArticleVendu = ArticleVendu.objects.first()
        self.assertEqual(art_v.article, boisson)
        self.assertEqual(art_v.qty, qty)
        self.assertEqual(art_v.total(), total)
        self.assertEqual(art_v.responsable, responsable)
        self.assertEqual(art_v.pos, pdv)
        self.assertEqual(art_v.moyen_paiement.categorie, MoyenPaiement.CASH)
        self.assertIsNone(art_v.carte)

        # Paiement en carte bancaire:
        qty = 6
        total = dround((boisson.prix * qty))
        json_achats = {"articles": [{"pk": f"{boisson.pk}", "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": total,
                       "moyen_paiement": 'carte_bancaire',
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('route'), f"transaction_carte_bancaire")
        self.assertEqual(response.json().get('somme_totale'), f"{total}")
        art_v: ArticleVendu = ArticleVendu.objects.first()
        self.assertEqual(art_v.article, boisson)
        self.assertEqual(art_v.qty, qty)
        self.assertEqual(art_v.total(), total)
        self.assertEqual(art_v.responsable, responsable)
        self.assertEqual(art_v.pos, pdv)
        self.assertEqual(art_v.moyen_paiement.categorie, MoyenPaiement.CREDIT_CARD_NOFED)
        self.assertIsNone(art_v.carte)

        return art_v

    def ajout_monnaie(self, carte=None):
        recharge_local_euro_10: Articles = Articles.objects.get(
            name="+10",
            methode_choices=Articles.RECHARGE_EUROS,
        )

        self.assertIsInstance(recharge_local_euro_10, Articles)
        self.assertEqual(recharge_local_euro_10.prix, 10)
        self.assertFalse(recharge_local_euro_10.fractionne)
        self.assertFalse(recharge_local_euro_10.archive)

        primary_card = CarteMaitresse.objects.filter(
            points_de_vente__isnull=False,
            carte__isnull=False,
            carte__membre__isnull=False,
        ).first()

        responsable: Membre = primary_card.carte.membre

        # Ce point de vente doit être tout seul
        pdv = PointDeVente.objects.get(comportement=PointDeVente.CASHLESS)
        self.assertIsInstance(pdv, PointDeVente)

        # Recharge sans carte -> erreur
        qty = 2
        total: Decimal = dround((recharge_local_euro_10.prix * qty))
        json_achats = {"articles": [{"pk": str(recharge_local_euro_10.pk), "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": total,
                       "moyen_paiement": 'carte_bancaire',
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        if response.status_code != 406:
            import ipdb;
            ipdb.set_trace()

        self.assertEqual(response.status_code, 406)
        self.assertTrue(response.json().get('non_field_errors'))

        # TEST avec carte sans membre
        # Si la carte n'est pas donné dans l'argument de la fonction
        carte = CarteCashless.objects.filter(
            membre__isnull=True,
            cartes_maitresses__isnull=True,
        ).first()

        json_achats['tag_id'] = carte.tag_id
        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(carte.total_monnaie(), total)
        self.assertIsNone(carte.membre)

        # TEST avec carte avec membre
        carte = CarteCashless.objects.filter(
            membre__isnull=False,
            cartes_maitresses__isnull=True,
        ).first()

        json_achats['tag_id'] = carte.tag_id
        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        data_response = response.json()
        self.assertEqual(data_response.get('route'), f"transaction_ajout_monnaie_virtuelle")
        self.assertEqual(data_response.get('somme_totale'), f"{total}")
        carte_in_response = data_response.get('carte')
        self.assertEqual(carte_in_response.get('tag_id'), carte.tag_id)
        self.assertEqual(carte_in_response.get('number'), carte.number)
        self.assertEqual(carte_in_response.get('uuid_qrcode'), f"{carte.uuid_qrcode}")
        self.assertEqual(carte_in_response.get('membre_name'), carte.membre.name)
        self.assertEqual(carte.total_monnaie(), total)
        self.assertTrue(carte_in_response.get('cotisation_membre_a_jour_booleen'))
        assets_in_response = carte_in_response.get('assets')
        assets_db = carte.assets.all()
        for asset in assets_in_response:
            asset_db = assets_db.get(carte=carte, monnaie__pk=asset.get('monnaie'))
            self.assertEqual(asset.get('monnaie_name'), asset_db.monnaie.name)
            self.assertEqual(dround(asset.get('qty')), total)
            self.assertEqual(asset_db.qty, total)

        art_vendu: ArticleVendu = ArticleVendu.objects.first()

        self.assertEqual(art_vendu.article, recharge_local_euro_10)
        self.assertEqual(art_vendu.total(), total)
        self.assertEqual(art_vendu.responsable, responsable)
        self.assertEqual(art_vendu.pos, pdv)
        self.assertEqual(art_vendu.moyen_paiement.categorie, MoyenPaiement.CREDIT_CARD_NOFED)
        self.assertEqual(art_vendu.carte, carte)

        # TEST avec carte avec wallet ephère et token cadeau
        carte2 = CarteCashless.objects.filter(
            membre__isnull=True,
            cartes_maitresses__isnull=True,
            assets__isnull=True,
        ).first()

        recharge_gift_euro_5: Articles = Articles.objects.get(
            prix=5,
            methode_choices=Articles.RECHARGE_CADEAU,
        )
        qty_gift = 2
        total_gift: Decimal = dround((recharge_gift_euro_5.prix * qty_gift))

        json_achats_gift = {"articles": [{"pk": str(recharge_gift_euro_5.pk), "qty": qty_gift}],
                            "pk_responsable": f"{responsable.pk}",
                            "pk_pdv": f"{pdv.pk}",
                            "total": total_gift,
                            "moyen_paiement": 'nfc',
                            'tag_id': carte2.tag_id,
                            }

        response_gift = self.client.post('/wv/paiement',
                                         data=json.dumps(json_achats_gift, cls=DjangoJSONEncoder),
                                         content_type="application/json",
                                         HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        data_response_gift = response_gift.json()
        self.assertEqual(data_response_gift.get('route'), f"transaction_ajout_monnaie_virtuelle")

        carte_in_response_gift = data_response_gift.get('carte')
        self.assertEqual(carte_in_response_gift.get('tag_id'), carte2.tag_id)
        self.assertEqual(carte_in_response_gift.get('number'), carte2.number)
        self.assertEqual(carte_in_response_gift.get('uuid_qrcode'), f"{carte2.uuid_qrcode}")
        self.assertEqual(carte_in_response_gift.get('membre_name'), '---')
        self.assertEqual(carte_in_response_gift.get('total_monnaie'), f"{total_gift}")
        self.assertEqual(carte2.total_monnaie(), total_gift)
        self.assertFalse(carte_in_response_gift.get('cotisation_membre_a_jour_booleen'))
        assets_in_response_gift = carte_in_response_gift.get('assets')
        assets_db_gift = carte2.assets.all()
        for asset in assets_in_response_gift:
            asset_db_gift = assets_db_gift.get(carte=carte2, monnaie__pk=asset.get('monnaie'))
            self.assertEqual(asset.get('monnaie_name'), asset_db_gift.monnaie.name)
            self.assertEqual(dround(asset.get('qty')), total_gift)
            self.assertEqual(asset_db_gift.qty, total_gift)

        art_vendu: ArticleVendu = ArticleVendu.objects.first()

        self.assertEqual(art_vendu.article, recharge_gift_euro_5)
        self.assertEqual(art_vendu.total(), total_gift)
        self.assertEqual(art_vendu.responsable, responsable)
        self.assertEqual(art_vendu.pos, pdv)
        self.assertEqual(art_vendu.carte, carte2)
        # Paiement cadeau, moyen = None
        self.assertEqual(art_vendu.moyen_paiement, None)

        return carte

    def check_hash_fedow(self, hash, total, carte):
        fedowAPI = FedowAPI()
        serialized_transaction = fedowAPI.transaction.get_from_hash(hash)
        self.assertEqual(serialized_transaction['amount'], int(total * 100))
        self.assertEqual(serialized_transaction['card']['first_tag_id'], carte.tag_id)
        return serialized_transaction

    def paiement_cashless_external_token(self, carte):
        plat_duj: Articles = Articles.objects.create(
            name="Plat Duj",
            prix=8,
            prix_achat="1",
            methode_choices=Articles.VENTE,
        )
        primary_card = CarteMaitresse.objects.first()
        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(name="Boutique")
        ex_total_monnaie = carte.total_monnaie()

        qty = 1
        total: Decimal = dround((plat_duj.prix * qty))
        json_achats = {"articles": [{"pk": f"{plat_duj.pk}", "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": total,
                       "tag_id": carte.tag_id,
                       "moyen_paiement": 'nfc',
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.check_carte_bis(carte, dround(ex_total_monnaie - total))

        # On va vérifier que la monnaie prise en compte est bien extérieure
        avs = ArticleVendu.objects.filter(carte=carte)
        if avs.count() == 3:
            # C'est un test from scratch !
            # On a une recharge cadeau, une recharge euro et une vente
            # La carte contient des cadeaux et des euros, seul les cadeau doivent être dépensé
            av = avs.first()
            self.assertEqual(av.moyen_paiement.categorie, MoyenPaiement.LOCAL_GIFT)
            self.assertEqual(av.total(), total)

            # On récupère le hash de la transaction cadeau
            hash_fedow = av.hash_fedow
            hash_avs = ArticleVendu.objects.filter(hash_fedow=hash_fedow)
            self.assertEqual(hash_avs.count(), 1)
            self.check_hash_fedow(hash_fedow, total, carte)


        elif avs.count() == 1:
            # C'est un test deuxieme passage
            # L'origin de la carte est extérieure, on ne vois que les euros chargé
            av = avs.first()
            self.assertEqual(av.moyen_paiement.categorie, MoyenPaiement.EXTERIEUR_FED)
            self.assertEqual(av.total(), total)

            # On récupère le hash de la transaction cadeau
            hash_fedow = av.hash_fedow
            hash_avs = ArticleVendu.objects.filter(hash_fedow=hash_fedow)
            self.assertEqual(hash_avs.count(), 1)
            self.check_hash_fedow(hash_fedow, total, carte)

        else:
            import ipdb;
            ipdb.set_trace()

    def paiement_cashless_virgule(self):
        primary_card = CarteMaitresse.objects.first()
        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(name="Boutique")
        carte1, carte2 = self.create_2_card_and_charge_it()

        biere5: Articles = Articles.objects.create(
            name="Biere5",
            prix=2.5,
            prix_achat="1",
            methode_choices=Articles.VENTE,
        )

        biere8: Articles = Articles.objects.create(
            name="Biere8",
            prix=2.8,
            prix_achat="1",
            methode_choices=Articles.VENTE,
        )

        # Première carte
        json_achats = {"articles": [
            {"pk": f"{biere5.pk}", "qty": 1},
            {"pk": f"{biere8.pk}", "qty": 1},
        ],
            "pk_responsable": f"{responsable.pk}",
            "pk_pdv": f"{pdv.pk}",
            "total": 5.30,
            "tag_id": carte1.tag_id,
            "moyen_paiement": 'nfc',
        }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(carte1.total_monnaie(), dround(4.70))
        avs = ArticleVendu.objects.filter(carte=carte1, pos=pdv)
        self.assertEqual(avs.count(), 3)
        # Total :
        self.assertEqual(sum([av.total() for av in avs]), dround(5.30))
        self.assertEqual(str(sum([av.total() for av in avs])), str(dround(5.30)))
        # Quantitée :
        self.assertEqual(sum([av.qty for av in avs]), 2)
        # Fedow :
        hashs = {}
        for av in avs:
            if hashs.get(av.hash_fedow):
                hashs[av.hash_fedow] += dround(av.total())
            else:
                hashs[av.hash_fedow] = dround(av.total())

        for hash, total in hashs.items():
            transac = self.check_hash_fedow(hash, total, carte1)

        # Paiement qui peu generer beaucoup de chiffre apres la virgule :
        json_achats = {"articles": [
            {"pk": f"{biere8.pk}", "qty": 3},
        ],
            "pk_responsable": f"{responsable.pk}",
            "pk_pdv": f"{pdv.pk}",
            "total": 8.40,
            "tag_id": carte2.tag_id,
            "moyen_paiement": 'nfc',
        }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(carte2.total_monnaie(), dround(1.60))
        avs2 = ArticleVendu.objects.filter(carte=carte2, pos=pdv)
        # Fedow :
        hashs2 = {}
        for av in avs2:
            if hashs2.get(av.hash_fedow):
                hashs2[av.hash_fedow] += dround(av.total())
            else:
                hashs2[av.hash_fedow] = dround(av.total())

        for hash, total in hashs2.items():
            transac = self.check_hash_fedow(hash, total, carte2)

    def paiement_cashless(self):

        boisson: Articles = Articles.objects.create(
            name="Boisson_Test",
            prix=10,
            prix_achat="1",
            methode_choices=Articles.VENTE,
        )

        primary_card = CarteMaitresse.objects.first()
        self.assertIsInstance(primary_card, CarteMaitresse)
        self.assertIsInstance(primary_card.carte, CarteCashless)
        responsable: Membre = primary_card.carte.membre
        self.assertIsInstance(responsable, Membre)

        pdv = PointDeVente.objects.get(name="Boutique")
        self.assertIsInstance(pdv, PointDeVente)

        carte = CarteCashless.objects.filter(
            membre__isnull=False,
            cartes_maitresses__isnull=True,
            assets__isnull=False,
            assets__monnaie__categorie=MoyenPaiement.LOCAL_EURO,
            assets__qty__gte=10,
        ).first()

        self.assertTrue(carte.assets.filter(monnaie__categorie=MoyenPaiement.LOCAL_EURO).exists())
        self.assertTrue(carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_EURO).qty > 0)
        token_avant_paiement = carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_EURO).qty
        # Paiement en cashless :

        qty = 1
        total: Decimal = dround((boisson.prix * qty))
        self.assertIsInstance(total, Decimal)
        self.assertEqual(total, boisson.prix)
        self.assertEqual(total, dround(10))
        json_achats = {"articles": [{"pk": f"{boisson.pk}", "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": total,
                       "tag_id": carte.tag_id,
                       "moyen_paiement": 'nfc',
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('route'), f"transaction_nfc")
        self.assertEqual(response.json().get('somme_totale'), f"{total}")
        art_v: ArticleVendu = ArticleVendu.objects.first()
        self.assertEqual(art_v.article, boisson)
        self.assertEqual(art_v.qty, qty)
        self.assertEqual(art_v.total(), total)
        self.assertEqual(art_v.responsable, responsable)
        self.assertEqual(art_v.pos, pdv)
        self.assertEqual(art_v.moyen_paiement.categorie, MoyenPaiement.LOCAL_EURO)
        self.assertIsNotNone(art_v.carte)
        self.assertEqual(art_v.carte, carte)

        carte.refresh_from_db()
        # Le paiement a bien été effectué en DB
        self.assertEqual(carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_EURO).qty,
                         dround(token_avant_paiement - total))

        return carte

    def check_carte(self):
        check_carte_data = {
            "tag_id_client": "12345678",
        }
        response = self.client.post('/wv/check_carte',
                                    data=json.dumps(check_carte_data, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 404)

        monnaie_e = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        asset_e = self.carte_chargee.assets.get(monnaie=monnaie_e)

        self.carte_chargee.refresh_from_db()
        check_carte_data = {
            "tag_id_client": self.carte_chargee.tag_id,
        }
        response = self.client.post('/wv/check_carte',
                                    data=json.dumps(check_carte_data, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content.get('tag_id'), f"{self.carte_chargee.tag_id}")
        assets = content.get('assets')

        self.assertEqual(Decimal(assets[0].get('qty')), asset_e.qty)
        self.assertEqual(assets[0].get('monnaie'), f"{monnaie_e.pk}")

    def create_badgeuse(self):
        self.assertFalse(MoyenPaiement.objects.filter(categorie=MoyenPaiement.BADGE).exists())
        badgeuse_creation()
        self.assertTrue(MoyenPaiement.objects.filter(categorie=MoyenPaiement.BADGE).exists())

    def send_asset_to_fedow_with_api(self):
        # On check la fédération actuelle, nous devons avoir que la monnaie fedow stripe
        config = Configuration.get_solo()
        get_accepted_assets = self.fedowAPI.place.get_accepted_assets()
        self.assertEqual(len(get_accepted_assets), 1)
        self.assertEqual(get_accepted_assets[0].get('category'), 'FED')

        # Avec le script de popdb, on a déjà des assets de type local et gift
        # On change le nom pour ne pas avoir l'erreur de doublon dans fedow
        # Dans le futur, il faudra créer des assets ici from scratch
        fake = Faker()
        set_list = set((fake.currency_name(), fake.currency_code()) for x in range(10))
        # import ipdb; ipdb.set_trace()
        name, currency_code = set_list.pop()
        mp_primary = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        mp_primary.currency_code = currency_code
        mp_primary.name = f"EURO2_{config.structure}"
        mp_primary.save()

        name, currency_code = set_list.pop()
        mp_gift = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)
        mp_gift.currency_code = currency_code
        mp_gift.name = f"CADEAU2_{config.structure}"
        mp_gift.save()

        # Envoie trois assets : euros, cadeau et adhésion
        responses = self.fedowAPI.send_assets_from_cashless()
        # Création vers fedow de : Badgeuse + assets e + asset cadeau + adhésion
        if len(responses) != 4:
            import ipdb;
            ipdb.set_trace()
        self.assertEqual(len(responses), 4)

        assets_pk = [str(asset.pk) for asset in MoyenPaiement.objects.all()]
        assets_pk.append(str(Configuration.get_solo().methode_adhesion.pk))
        for response in responses:
            self.assertEqual(response.status_code, 201)
            self.assertIn(response.json()['uuid'], assets_pk)
            self.assertFalse(response.json()['is_stripe_primary'])

        # On relance la demande des assets acceptés, les nouveaux doivent y être
        get_accepted_assets = self.fedowAPI.place.get_accepted_assets()

        if len(get_accepted_assets) != 5:
            import ipdb;
            ipdb.set_trace()
        self.assertEqual(len(get_accepted_assets), 5)

        cats = [asset.get('category') for asset in get_accepted_assets]
        self.assertEqual(len(cats), 5)
        self.assertIn('FED', cats)
        self.assertIn('TNF', cats)
        self.assertIn('TLF', cats)
        self.assertIn('SUB', cats)
        self.assertIn('BDG', cats)

        return responses

    def send_card_to_fedow_with_api(self):
        cards = CarteCashless.objects.all()
        response = self.fedowAPI.NFCcard.create(cards)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(int(response.json()), cards.count())

        return response

    def creation_wallet_carte_vierge_et_email(self):
        fedowAPI = FedowAPI()
        cartes = CarteCashless.objects.filter(membre__isnull=False, wallet__isnull=True)[:2]
        self.assertEqual(cartes.count(), 2)
        for carte in cartes:
            # Link de l'email à la carte via le code nfc
            wallet: Wallet = fedowAPI.NFCcard.link_user(email=carte.membre.email, card=carte)
            wallet_uuid = wallet.uuid
            self.assertIsInstance(wallet_uuid, UUID)
            self.assertIsInstance(wallet_uuid, UUID)

            # on vérifie avec le rerieve
            serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
            self.assertEqual(serialized_card.get('wallet').get('uuid'), wallet_uuid)
            self.assertEqual(serialized_card.get('uuid'), carte.pk)
            self.assertFalse(serialized_card.get('is_wallet_ephemere'))

            # Le set_user a enregistré le wallet dans la carte
            carte.refresh_from_db()
            self.assertEqual(serialized_card['wallet']['uuid'], carte.wallet.uuid)

        self.assertEqual(cartes[0].membre.wallet, cartes[0].wallet)
        self.assertEqual(cartes[1].membre.wallet, cartes[1].wallet)

    #TODO: Uniquement possible avec Billetterie dans le futur, c'est la bas que la clé rsa est stockée
    def creation_wallet_avec_email_seul(self):
        fedowAPI = FedowAPI()
        membres = Membre.objects.filter(CarteCashless_Membre__isnull=True, email__isnull=False, wallet__isnull=True)[:4]
        self.assertEqual(membres.count(), 4)
        for membre in membres:
            # Link de l'email à la carte via le code nfc
            wallet: Wallet = fedowAPI.wallet.create_from_email(email=membre.email)
            wallet_uuid = wallet.uuid
            self.assertIsInstance(wallet, Wallet)
            self.assertIsInstance(wallet_uuid, UUID)
            membre.refresh_from_db()
            self.assertEqual(membre.wallet.uuid, wallet_uuid)

    def same_membre_different_card(self):
        fedowAPI = FedowAPI()
        membre = Membre.objects.filter(
            CarteCashless_Membre__isnull=True,
            email__isnull=False,
        ).first()
        self.assertIsNotNone(membre)
        cartes = CarteCashless.objects.filter(membre__isnull=True, wallet__isnull=True)[:2]
        self.assertEqual(cartes.count(), 2)
        for carte in cartes:
            # Link de l'email à la carte via le code nfc
            wallet: Wallet = fedowAPI.NFCcard.link_user(email=membre.email, card=carte)
            wallet_uuid = wallet.uuid
            self.assertIsInstance(wallet, Wallet)
            self.assertIsInstance(wallet_uuid, UUID)

            # on vérifie avec le rerieve
            serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
            self.assertEqual(serialized_card.get('wallet').get('uuid'), wallet_uuid)
            self.assertEqual(serialized_card.get('uuid'), carte.pk)
            self.assertFalse(serialized_card.get('is_wallet_ephemere'))

            # Le set_user a enregistré le wallet dans la carte
            carte.refresh_from_db()
            self.assertIsInstance(carte.wallet, Wallet)
            self.assertEqual(serialized_card['wallet']['uuid'], carte.wallet.uuid)

        self.assertEqual(cartes[0].membre.wallet, cartes[0].wallet)
        self.assertEqual(cartes[1].membre.wallet, cartes[1].wallet)
        self.assertEqual(cartes[0].membre, membre)
        self.assertEqual(cartes[1].membre, membre)

        return membre

    def creation_wallet_card_seule(self):
        # Les cartes n'ont pas de wallet, on check qu'ils sont créé avec l'envoie à Fedow
        fedowAPI = FedowAPI()
        cartes = CarteCashless.objects.filter(membre__isnull=True, wallet__isnull=True)[:2]
        self.assertEqual(cartes.count(), 2)
        for carte in cartes:
            serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
            # fedowAPI a créé un wallet
            carte.refresh_from_db()
            self.assertIsInstance(carte.wallet, Wallet)
            self.assertEqual(serialized_card.get('wallet').get('uuid'), carte.wallet.uuid)
            self.assertTrue(serialized_card['is_wallet_ephemere'])

    def send_adh_to_fedow_with_api(self):
        list_adh = (membre for membre in Membre.objects.all() if membre.a_jour_cotisation())
        fedowAPI = FedowAPI()
        for membre in list_adh:
            carte = membre.CarteCashless_Membre.first()
            wallet = carte.wallet or membre.wallet
            if not wallet:
                wallet: Wallet = fedowAPI.NFCcard.link_user(email=carte.membre.email, card=carte)

            adhesion = fedowAPI.subscription.create(
                wallet=f"{wallet.uuid}",
                amount=int(membre.cotisation * 100),
                date=membre.date_derniere_cotisation,
                user_card_firstTagId=carte.tag_id,
            )

            self.assertIsInstance(adhesion, dict)
            self.assertEqual(adhesion.get('amount'), int(self.config.prix_adhesion * 100))
            self.assertEqual(adhesion.get('action'), TransactionValidator.SUBSCRIBE)
            self.assertEqual(adhesion.get('sender'), UUID(self.config.fedow_place_wallet_uuid))
            carte.refresh_from_db()
            self.assertEqual(adhesion.get('receiver'), carte.wallet.uuid)
            membre.refresh_from_db()
            self.assertEqual(adhesion.get('receiver'), membre.wallet.uuid)
            self.assertEqual(adhesion.get('card')['first_tag_id'], carte.tag_id)
            self.assertEqual(adhesion.get('subscription_start_datetime').date(), membre.date_derniere_cotisation)

            # TODO: vérifier le token uuid créé dans le cashless

    def fedow_wallet_with_tagid(self):
        card = CarteCashless.objects.first()
        self.assertIsNotNone(card.tag_id)
        self.assertIsNotNone(card.uuid_qrcode)
        self.assertIsNotNone(card.number)

        fedowAPI = FedowAPI()
        serialized_card = fedowAPI.NFCcard.retrieve(card.tag_id)

        wallet = serialized_card.get('wallet')
        self.assertIsInstance(wallet, dict)
        self.assertIsInstance(wallet.get('uuid'), type(uuid4()))
        self.assertEqual(card.get_wallet().uuid, wallet.get('uuid'))

        data_for_laboutik = fedowAPI.card_wallet_to_laboutik(serialized_card)
        self.assertIsInstance(data_for_laboutik, dict)
        self.assertIsInstance(data_for_laboutik.get('total_monnaie'), Decimal)
        self.assertIsInstance(data_for_laboutik.get('assets'), list)
        self.assertEqual(data_for_laboutik.get('first_tag_id'), card.tag_id)

        return serialized_card

    def refill_card_wallet(self):
        fedowAPI = FedowAPI()
        asset_local_euro = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        carte_primaire = CarteMaitresse.objects.first().carte

        cartes_a_tester = []
        carte_avec_wallet_membre = CarteCashless.objects.filter(membre__wallet__isnull=False).first()
        self.assertIsNotNone(carte_avec_wallet_membre)
        cartes_a_tester.append(carte_avec_wallet_membre)
        carte_avec_wallet_ephemere = CarteCashless.objects.filter(wallet__isnull=False, membre__isnull=True).first()
        self.assertIsNotNone(carte_avec_wallet_ephemere)
        cartes_a_tester.append(carte_avec_wallet_ephemere)

        for carte in cartes_a_tester:
            wallet: UUID = carte.get_wallet()
            self.assertIsInstance(wallet, Wallet)

            serialized_transaction = fedowAPI.transaction.refill_wallet(
                amount=4242,
                wallet=f"{wallet.uuid}",
                asset=f"{asset_local_euro.pk}",
                user_card_firstTagId=f"{carte.tag_id}",
                primary_card_fisrtTagId=carte_primaire.tag_id,
            )

            self.assertIsInstance(serialized_transaction, dict)
            self.assertEqual(serialized_transaction.get('amount'), 4242)
            self.assertEqual(serialized_transaction.get('action'), TransactionValidator.REFILL)
            self.assertEqual(serialized_transaction.get('sender'), UUID(self.config.fedow_place_wallet_uuid))
            self.assertEqual(serialized_transaction.get('receiver'), wallet.uuid)
            self.assertEqual(serialized_transaction.get('card')['first_tag_id'], carte.tag_id)
            self.assertEqual(serialized_transaction.get('primary_card'), carte_primaire.pk)
            self.assertIsNotNone(serialized_transaction.get('verify_hash'))

            # Vérification avec le retrieve
            serialized_card = fedowAPI.NFCcard.retrieve(f"{carte.tag_id}")
            self.assertIsInstance(serialized_card['wallet']['tokens'], list)
            tokens = [(token['asset_uuid'], token['value']) for token in serialized_card['wallet']['tokens']]
            self.assertIn((asset_local_euro.pk, 4242), tokens)
            if carte == carte_avec_wallet_membre:
                self.assertEqual(carte.wallet, carte.membre.wallet)
                self.assertFalse(serialized_card.get('is_wallet_ephemere'))
            if carte == carte_avec_wallet_ephemere:
                self.assertTrue(serialized_card.get('is_wallet_ephemere'))

            # TODO: tester que l'asset interne est bien a jour

    def refill_user_wallet(self):
        fedowAPI = FedowAPI()
        asset_local_euro = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)

        membre = Membre.objects.filter(wallet__isnull=False, CarteCashless_Membre__isnull=True).first()
        wallet: UUID = membre.wallet
        self.assertIsInstance(wallet, Wallet)

        serialized_transaction = fedowAPI.transaction.refill_wallet(
            amount=4242,
            wallet=f"{wallet.uuid}",
            asset=f"{asset_local_euro.pk}",
        )
        # Pas de carte ni de carte primaire : Indispensable pour un refill
        self.assertEqual(serialized_transaction, 400)

    def link_wallet_ephemere_to_user(self):
        fedowAPI = FedowAPI()
        # Les user sont déja créé et ont un wallet, mais pas de carte
        membres = Membre.objects.filter(CarteCashless_Membre__isnull=True, wallet__isnull=False)[:2]
        self.assertEqual(membres.count(), 2)
        # les cartes ont un wallet ephemère, mais pas d'user
        cartes = CarteCashless.objects.filter(membre__isnull=True, wallet__isnull=False)[:2]
        self.assertEqual(cartes.count(), 2)
        # les cartes ont un wallet et un user, on testera qu'on ne peut pas
        cartes_membre = CarteCashless.objects.filter(membre__isnull=False, wallet__isnull=False)[:2]
        self.assertEqual(cartes.count(), 2)

        # on charge des sous sur les cartes avec wallet ephemere
        for carte in cartes:
            ex_total = carte.total_monnaie()
            self.ajout_monnaie_bis(carte=carte, qty=5)
            self.check_carte_bis(carte=carte, total=ex_total + 10)

        # On lie les deux ensemble, fusion de wallet !
        for membre, carte, cartemembre in \
                ((membres[0], cartes[0], cartes_membre[0]), (membres[1], cartes[1], cartes_membre[1])):

            # On test sur des cartes déja membrées :
            try:
                fedowAPI.NFCcard.link_user(email=membre.email, card=cartemembre)
            except Exception as e:
                self.assertEqual(e.args[0], "Card already linked to another member")
            else:
                # on test que l'exception a bien été levé. Ceci ne devrait jamais se produire :
                self.assertFalse("L'exception précédente n'a pas été levé.")

            # Link de l'email à la carte via le code nfc
            before_fusions_serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
            ephemere_wallet_uuid = before_fusions_serialized_card['wallet']['uuid']

            # check qu'il y avait bien des token sur la carte avant sinon ils ne seront pas créé lors de la fusion
            before_tokens = [(token['asset_uuid'], token['value']) for token in
                             before_fusions_serialized_card['wallet']['tokens'] if token['value'] > 0]

            self.assertTrue(before_fusions_serialized_card.get('is_wallet_ephemere'))

            # Fusion des wallets
            wallet = fedowAPI.NFCcard.link_user(email=membre.email, card=carte)
            self.assertIsInstance(wallet, Wallet)

            # on vérifie avec le rerieve
            serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
            new_wallet_uuid = serialized_card['wallet']['uuid']
            after_tokens = [(token['asset_uuid'], token['value']) for token in serialized_card['wallet']['tokens']]

            self.assertEqual(serialized_card.get('wallet').get('uuid'), wallet.uuid)
            self.assertEqual(serialized_card.get('uuid'), carte.pk)
            self.assertFalse(serialized_card.get('is_wallet_ephemere'))
            if before_tokens != after_tokens:
                import ipdb;
                ipdb.set_trace()
            self.assertEqual(before_tokens, after_tokens)
            self.assertNotEqual(ephemere_wallet_uuid, new_wallet_uuid)

            # Vérification que le précédent wallet est bien vide
            ex_wallet = fedowAPI.wallet.retrieve(f"{before_fusions_serialized_card['wallet']['uuid']}")
            # import ipdb; ipdb.set_trace()
            # self.assertTrue(len(ex_wallet['tokens']) > 0)
            for tokens in ex_wallet['tokens']:
                self.assertEqual(tokens['value'], 0)

    def user_to_place_transaction(self):
        fedowAPI = FedowAPI()
        asset_local_euro = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)

        wallet = self.serialized_card['wallet']
        first_tag_id = self.serialized_card['first_tag_id']
        carte_primaire = CarteMaitresse.objects.first().carte

        serialized_transaction_w2w = fedowAPI.transaction.to_place(
            amount=2121,
            wallet=f"{wallet['uuid']}",
            asset=f"{asset_local_euro.pk}",
            user_card_firstTagId=first_tag_id,
            primary_card_fisrtTagId=carte_primaire.tag_id,
        )

        self.assertIsInstance(serialized_transaction_w2w, dict)
        if serialized_transaction_w2w.get('amount') != 2121:
            import ipdb;
            ipdb.set_trace()
        self.assertEqual(serialized_transaction_w2w.get('amount'), 2121)
        self.assertEqual(serialized_transaction_w2w.get('action'), TransactionValidator.SALE)
        self.assertEqual(serialized_transaction_w2w.get('receiver'), UUID(self.config.fedow_place_wallet_uuid))
        self.assertEqual(serialized_transaction_w2w.get('sender'), wallet.get('uuid'))
        self.assertEqual(serialized_transaction_w2w.get('card')['first_tag_id'], first_tag_id)
        self.assertEqual(serialized_transaction_w2w.get('primary_card'), carte_primaire.pk)
        self.assertIsNotNone(serialized_transaction_w2w.get('verify_hash'))

        # TODO : check l'uuid du token fedow == uuid asset cashless

        # TODO: Checker une carte non authorisé (get_authority_delegation)
        return serialized_transaction_w2w

    def remboursement_front(self):
        config = Configuration.get_solo()
        primary_card = CarteMaitresse.objects.first()
        if not primary_card:
            import ipdb; ipdb.set_trace()

        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(name="Boutique")
        carte, carte_bis = self.create_2_card_and_charge_it()

        self.check_carte_bis(carte=carte, total=10)

        article_vider_carte: Articles = Articles.objects.get(
            methode_choices=Articles.VIDER_CARTE,
        )

        if not responsable:
            import ipdb; ipdb.set_trace()

        json_achats = {"articles": [{"pk": f"{article_vider_carte.pk}", "qty": 1}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": f"0",
                       "tag_id": f"{carte.tag_id}",
                       "moyen_paiement": 'nfc',
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content.get('route'), f"transaction_vider_carte")
        # cadeau + euro = 10
        self.assertEqual(content.get('total_sur_carte_avant_achats'), f"10.00")
        # A rembourser = 5
        self.assertEqual(content.get('somme_totale'), f"5.00")

        self.check_carte_bis(carte=carte, total=0)

        art_v = ArticleVendu.objects.first()
        self.assertEqual(art_v.moyen_paiement.categorie, MoyenPaiement.CASH)
        self.assertEqual(art_v.total(), Decimal(-5.00))

    def remboursement_front_after_stripe_fed(self):
        config = Configuration.get_solo()
        primary_card = CarteMaitresse.objects.first()
        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(name="Boutique")

        assets = Assets.objects.filter(monnaie__categorie=MoyenPaiement.STRIPE_FED, qty=42)
        self.assertTrue(assets.exists())
        carte = assets.first().carte
        ex_total_monnaie = carte.total_monnaie()

        self.assertTrue(ex_total_monnaie >= 42)
        self.check_carte_bis(carte=carte, total=ex_total_monnaie)

        # On rajoute local euro et local cadeau pour pouvoir les vider ensuite
        self.ajout_monnaie_bis(carte=carte, qty=5)
        self.check_carte_bis(carte=carte, total=ex_total_monnaie + 10)

        ex_total_asset_euro = carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_EURO).qty
        self.assertTrue(ex_total_asset_euro >= 5)

        article_vider_carte: Articles = Articles.objects.get(
            methode_choices=Articles.VIDER_CARTE,
        )

        json_achats = {"articles": [{"pk": f"{article_vider_carte.pk}", "qty": 1}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": f"0",
                       "tag_id": f"{carte.tag_id}",
                       "moyen_paiement": 'nfc',
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content.get('route'), f"transaction_vider_carte")
        # cadeau + euro = 10
        self.assertEqual(content.get('total_sur_carte_avant_achats'), f"{ex_total_monnaie + 10}")
        carte.refresh_from_db()
        # On check que les deux assets locaux sont vide
        self.assertEqual(carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_EURO).qty, 0)
        self.assertEqual(carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_GIFT).qty, 0)
        # Mais il reste le fédéré
        self.assertEqual(carte.assets.get(monnaie__categorie=MoyenPaiement.STRIPE_FED).qty, 42)
        # A rembourser = uniquement les assets locaux euro
        self.assertEqual(content.get('somme_totale'), f"{ex_total_asset_euro}")

        self.check_carte_bis(carte=carte, total=42)

        art_v = ArticleVendu.objects.first()
        self.assertEqual(art_v.moyen_paiement.categorie, MoyenPaiement.CASH)
        self.assertEqual(art_v.total(), Decimal(-ex_total_asset_euro))

    def remboursement_et_vidage_direct_api(self):
        fedowAPI = FedowAPI()
        carte_primaire = CarteMaitresse.objects.first().carte

        # On fabrique une carte et on la charge :
        carte = self.create_card()
        self.ajout_monnaie_bis(carte=carte, qty=21)
        carte.refresh_from_db()
        wallet = carte.get_wallet()
        first_tag_id = carte.tag_id

        asset_euro_uuid = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO).pk
        asset_gift_uuid = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT).pk

        # Check carte pour vérifier ensuite la différence :
        ex_serialized_card = fedowAPI.NFCcard.retrieve(first_tag_id)

        self.assertEqual(ex_serialized_card['wallet']['uuid'], wallet.uuid)
        self.assertTrue(ex_serialized_card['is_wallet_ephemere'])
        tokens = ex_serialized_card['wallet']['tokens']

        # Deux token, euro et cadeau
        if len(tokens) != 2:
            import ipdb;
            ipdb.set_trace()

        self.assertEqual(len(tokens), 2)
        token_dict = {token['asset_uuid']: token['value'] for token in tokens}
        self.assertEqual(token_dict[asset_euro_uuid], 2100)
        self.assertEqual(token_dict[asset_gift_uuid], 2100)

        # Vidage de la carte :
        refund_data = fedowAPI.NFCcard.refund(
            user_card_firstTagId=first_tag_id,
            primary_card_fisrtTagId=carte_primaire.tag_id,
        )

        if not refund_data:
            import ipdb;
            ipdb.set_trace()
        self.assertIsInstance(refund_data, dict)

        # Le wallet n'a pas bougé ?
        carte.refresh_from_db()
        wallet = carte.get_wallet()
        self.assertEqual(ex_serialized_card['wallet']['uuid'], wallet.uuid)
        assets_cashless = carte.get_payment_assets()
        self.assertEqual(assets_cashless.get(monnaie__id=asset_euro_uuid).qty, 0)
        self.assertEqual(assets_cashless.get(monnaie__id=asset_gift_uuid).qty, 0)

        serialized_card = refund_data['serialized_card']
        before_refund_serialized_wallet = refund_data['before_refund_serialized_wallet']
        serialized_transactions = refund_data['serialized_transactions']

        self.assertEqual(ex_serialized_card['wallet'], before_refund_serialized_wallet)
        self.assertNotEqual(serialized_card['wallet'], before_refund_serialized_wallet)
        after_refund_token_dict = {token['asset_uuid']: token['value'] for token in serialized_card['wallet']['tokens']}
        self.assertEqual(after_refund_token_dict[asset_euro_uuid], 0)

        # TODO: checker federated
        self.assertEqual(len(serialized_transactions), 2)
        # Deux transactions mais seul le remboursement euro est dans le amount :
        self.assertEqual(serialized_transactions[0].get('amount'), 2100)
        self.assertEqual(serialized_transactions[0].get('action'), TransactionValidator.REFUND)
        self.assertTrue(serialized_transactions[0].get('verify_hash'))
        print(serialized_transactions[0].get('uuid'))

        self.assertEqual(serialized_transactions[1].get('amount'), 2100)
        self.assertEqual(serialized_transactions[1].get('action'), TransactionValidator.REFUND)
        self.assertTrue(serialized_transactions[1].get('verify_hash'))

        # Void de la carte, on rembourse et on rend la carte de nouveau vierge
        void_data = fedowAPI.NFCcard.void(
            user_card_firstTagId=first_tag_id,
            primary_card_fisrtTagId=carte_primaire.tag_id,
        )

        carte.refresh_from_db()
        self.assertNotEqual(ex_serialized_card['wallet']['uuid'], carte.wallet.uuid)
        self.assertIsNone(carte.membre)

        self.assertIsInstance(void_data, dict)
        # Carte void = carte avec wallet ephemere vide
        serialized_card_voided = void_data['serialized_card']
        self.assertEqual(serialized_card_voided['wallet']['tokens'], [])
        self.assertTrue(serialized_card_voided['is_wallet_ephemere'])

        before_refund_serialized_wallet_voided = void_data['before_refund_serialized_wallet']
        self.assertEqual(before_refund_serialized_wallet_voided, serialized_card['wallet'])

        # Vide car déja vidé juste avant.
        # On va tester un cas de void ou la carte n'est pas vide
        serialized_transactions = void_data['serialized_transactions']
        self.assertEqual(serialized_transactions, [])

    def refill_and_void(self):
        ###
        # Chargement d'une carte pour la void ensuite
        ###
        fedowAPI = FedowAPI()
        carte_primaire = CarteMaitresse.objects.first().carte

        asset_local_euro = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        asset_gift = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)

        carte = CarteCashless.objects.filter(membre__wallet__isnull=False).last()
        ex_total_euro = carte.total_monnaie(carte.assets.filter(monnaie=MoyenPaiement.get_local_euro()))
        ex_total_gift = carte.total_monnaie(carte.assets.filter(monnaie=MoyenPaiement.get_local_gift()))

        self.assertIsNotNone(carte)
        wallet: Wallet = carte.get_wallet()
        self.assertIsInstance(wallet, Wallet)
        serialized_new_transaction_euro = fedowAPI.transaction.refill_wallet(
            amount=6666,
            wallet=f"{wallet.uuid}",
            asset=f"{asset_local_euro.pk}",
            user_card_firstTagId=f"{carte.tag_id}",
            primary_card_fisrtTagId=carte_primaire.tag_id,
        )
        self.assertEqual(serialized_new_transaction_euro.get('amount'), 6666)
        self.assertEqual(serialized_new_transaction_euro.get('action'), TransactionValidator.REFILL)

        serialized_new_transaction_gift = fedowAPI.transaction.refill_wallet(
            amount=9999,
            wallet=f"{wallet.uuid}",
            asset=f"{asset_gift.pk}",
            user_card_firstTagId=f"{carte.tag_id}",
            primary_card_fisrtTagId=carte_primaire.tag_id,
        )
        self.assertEqual(serialized_new_transaction_gift.get('amount'), 9999)
        self.assertEqual(serialized_new_transaction_gift.get('action'), TransactionValidator.REFILL)

        ex_new_serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
        self.assertFalse(ex_new_serialized_card['is_wallet_ephemere'])
        tokens = ex_new_serialized_card['wallet']['tokens']
        self.assertTrue(len(tokens) >= 2)
        token_dict = {token['asset_uuid']: token['value'] for token in tokens}

        total_euro_after_refill = (6666 + (ex_total_euro * 100))
        total_gift_after_refill = (9999 + (ex_total_gift * 100))

        if (token_dict[asset_local_euro.pk] != total_euro_after_refill or
                token_dict[asset_gift.pk] != total_gift_after_refill):
            import ipdb;
            ipdb.set_trace()

        self.assertEqual(token_dict[asset_local_euro.pk], 6666 + (ex_total_euro * 100))
        self.assertEqual(token_dict[asset_gift.pk], 9999 + (ex_total_gift * 100))

        new_void_data = fedowAPI.NFCcard.void(
            user_card_firstTagId=carte.tag_id,
            primary_card_fisrtTagId=carte_primaire.tag_id,
        )

        self.assertIsInstance(new_void_data, dict)
        # Carte void = carte avec wallet ephemere vide
        before_refund_serialized_wallet_voided = new_void_data['before_refund_serialized_wallet']

        # Le void s'est bien passé : la carte est vide est le wallet est épemère
        serialized_card_voided = new_void_data['serialized_card']
        self.assertEqual(serialized_card_voided['wallet']['tokens'], [])
        self.assertTrue(serialized_card_voided['is_wallet_ephemere'])

        # Le before ressemble bien au retrieve précédent avant le void
        self.assertEqual(before_refund_serialized_wallet_voided, ex_new_serialized_card['wallet'])

        serialized_transactions_voided = new_void_data['serialized_transactions']

        self.assertEqual(len(serialized_transactions_voided), 2)
        self.assertEqual(serialized_transactions_voided[0].get('amount'), total_euro_after_refill)
        self.assertEqual(serialized_transactions_voided[0].get('action'), TransactionValidator.REFUND)
        self.assertTrue(serialized_transactions_voided[0].get('verify_hash'))
        self.assertEqual(serialized_transactions_voided[1].get('amount'), total_gift_after_refill)
        self.assertEqual(serialized_transactions_voided[1].get('action'), TransactionValidator.REFUND)
        self.assertTrue(serialized_transactions_voided[1].get('verify_hash'))

        # Checker que le void a retiré aussi le wallet du membre cashless
        carte.refresh_from_db()
        self.assertNotEqual(ex_new_serialized_card['wallet']['uuid'], carte.wallet.uuid)
        self.assertIsNone(carte.membre)
        serialized_card_voided = new_void_data['serialized_card']
        self.assertEqual(serialized_card_voided['wallet']['tokens'], [])
        self.assertTrue(serialized_card_voided['is_wallet_ephemere'])

        # L'ancien wallet existe toujours, mais il est vide
        wallet_empty = fedowAPI.wallet.retrieve(f"{wallet.uuid}")
        after_void_token_dict = {token['asset_uuid']: token['value'] for token in wallet_empty['tokens']}
        self.assertEqual(after_void_token_dict[asset_local_euro.pk], 0)
        self.assertEqual(after_void_token_dict[asset_gift.pk], 0)

    def check_carte_bis(self, carte, total):
        check_carte_data = {
            "tag_id_client": carte.tag_id,
        }
        response = self.client.post('/wv/check_carte',
                                    data=json.dumps(check_carte_data, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content.get('tag_id'), f"{carte.tag_id}")
        self.assertEqual(dround(content.get('total_monnaie')), dround(total))

    def ajout_monnaie_bis(self, carte=None, qty=None):
        recharge_local_euro_1: Articles = Articles.objects.get(
            name="+1",
            methode_choices=Articles.RECHARGE_EUROS,
        )

        recharge_local_gift_1: Articles = Articles.objects.get(
            name="Cadeau +1",
            methode_choices=Articles.RECHARGE_CADEAU,
        )

        primary_card = CarteMaitresse.objects.filter(
            carte__isnull=False,
            carte__membre__isnull=False,
        ).first()

        if not primary_card:
            import ipdb;
            ipdb.set_trace()

        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(comportement=PointDeVente.CASHLESS)

        total: Decimal = dround((recharge_local_euro_1.prix * qty))
        json_achats = {"articles": [{"pk": str(recharge_local_euro_1.pk), "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": total,
                       "moyen_paiement": 'carte_bancaire',
                       'tag_id': carte.tag_id,
                       }
        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        json_achats = {"articles": [{"pk": str(recharge_local_gift_1.pk), "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": total,
                       "moyen_paiement": 'nfc',
                       'tag_id': carte.tag_id,
                       }
        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

    def create_card(self, tag_id=None, number=None, qr_code=None):
        if not tag_id:
            tag_id = str(uuid4())[:8].upper()
        if not qr_code:
            qr_code = str(uuid4())
        if not number:
            number = qr_code[:8].upper()

        try:
            config = Configuration.get_solo()
            origin = Origin.objects.get(place__name=f"{config.structure}", generation=1)
        except Origin.DoesNotExist:
            origin = None

        carte = CarteCashless.objects.create(
            tag_id=f"{tag_id}",
            number=f"{number}",
            uuid_qrcode=f"{qr_code}",
            origin=origin,
        )
        config = Configuration.get_solo()
        if config.can_fedow():
            response = self.fedowAPI.NFCcard.create([carte, ])
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json(), '1')

        return carte

    def create_2_card_and_charge_it(self):
        config = Configuration.get_solo()

        try:
            config = Configuration.get_solo()
            origin = Origin.objects.get(place__name=f"{config.structure}", generation=1)
        except Origin.DoesNotExist:
            origin = None
        cartes = []

        # Création de deux cartes
        for i in range(2):
            fake_uuid = str(uuid4()).upper()
            cartes.append(CarteCashless.objects.create(
                tag_id=f"{str(uuid4())[:8].upper()}",
                number=f"{fake_uuid[:8]}",
                uuid_qrcode=f"{fake_uuid}",
                origin=origin,
            ))

        if config.can_fedow():
            response = self.fedowAPI.NFCcard.create(cartes)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json(), '2')

        # Chargement des cartes
        for carte in cartes:
            self.ajout_monnaie_bis(carte=carte, qty=5)
            self.check_carte_bis(carte=carte, total=10)

        return cartes

    def paiement_complementaire_transactions(self):
        primary_card = CarteMaitresse.objects.filter(
            carte__isnull=False, carte__membre__isnull=False).first()
        self.assertTrue(primary_card)
        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(name="Boutique")
        cartes = self.create_2_card_and_charge_it()

        carte: CarteCashless = cartes[0]
        total_carte = carte.total_monnaie()
        carte_bis: CarteCashless = cartes[1]
        total_carte_bis = carte_bis.total_monnaie()
        total_complementaire = total_carte + total_carte_bis

        # Fabrication d'un objet avec prix à virgule
        article: Articles = Articles.objects.create(
            name="article_test",
            prix=Decimal(4),
            prix_achat="1",
            methode_choices=Articles.VENTE,
        )

        # Solde insuffisant
        qty = 6
        total = dround(qty * article.prix)
        json_achats = {"articles": [{"pk": f"{article.pk}", "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": f"{total}",
                       "tag_id": f"{carte.tag_id}",
                       "moyen_paiement": 'nfc',
                       "complementaire": {
                           "manque": f"{dround(total - total_carte)}",
                           "moyen_paiement": "nfc",
                           "tag_id": f"{carte_bis.tag_id}",
                       }
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        content = response.json()
        message = content['message']
        self.assertEqual(message.get('msg'), 'Fonds insuffisants sur deuxieme carte.')
        self.assertEqual(dround(message.get('manque')), dround('4.00'))

        # Solde ok
        qty = 4
        total = dround(qty * article.prix)
        json_achats = {"articles": [{"pk": f"{article.pk}", "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": f"{total}",
                       "tag_id": f"{carte.tag_id}",
                       "moyen_paiement": 'nfc',
                       "complementaire": {
                           "manque": f"{dround(total - total_carte)}",
                           "moyen_paiement": "nfc",
                           "tag_id": f"{carte_bis.tag_id}",
                       }
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content.get('route'), 'transaction_nfc')
        self.assertEqual(dround(content.get('total_sur_carte_avant_achats')), total_complementaire)
        self.assertEqual(dround(content.get('somme_totale')), total)
        self.check_carte_bis(carte=carte, total=0)
        self.check_carte_bis(carte=carte_bis, total=(total_complementaire - total))

        # On prend les 4 derniers articles vendu :
        artsv = ArticleVendu.objects.order_by('-date_time')[:4]
        qty_total = dround(sum([art.qty for art in artsv]))
        self.assertEqual(qty_total, dround(4))
        ca_total = dround(sum([art.total() for art in artsv]))
        self.assertEqual(dround(ca_total), total)

        self.assertEqual(len(ArticleVendu.objects.filter(carte=carte, article=article)), 2)
        self.assertEqual(len(ArticleVendu.objects.filter(carte=carte_bis, article=article)), 2)
        self.assertEqual(len(ArticleVendu.objects.filter(article=article)), 4)

    def post_handshake(self):
        config = Configuration.get_solo()
        # Change le nom des assets pour lancer les test sans erreur de doublon
        asset_e = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        asset_e.name = f"EURO_{config.structure}"
        asset_e.save()
        asset_g = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)
        asset_g.name = f"CADEAU_{config.structure}"
        asset_g.save()

        asset_b = MoyenPaiement.objects.get(categorie=MoyenPaiement.BADGE)
        asset_b.name = f"BADGE_{config.structure}"
        asset_b.save()

        from fedow_connect.tasks import after_handshake
        settings.DEBUG = True
        after_handshake()

    def check_all_tokens_value(self):
        asset_e = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        total_local_euro = int(asset_e.total_tokens() * 100)
        self.assertTrue(total_local_euro > 0)

        asset_g = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)
        total_gift = int(asset_g.total_tokens() * 100)
        self.assertTrue(total_gift > 0)

        fedowAPI = FedowAPI()
        # Asset EURO
        asset_local_euro_fedow = fedowAPI.asset.retrieve(f"{asset_e.pk}")

        total_token_value = asset_local_euro_fedow.get('total_token_value')
        total_in_place = asset_local_euro_fedow.get('total_in_place')
        total_in_wallet_not_place = asset_local_euro_fedow.get('total_in_wallet_not_place')

        # Les wallets de carte  + wallet de lieu = toutes les valeurs de token dans FEDOW : on garde une trace de tout
        self.assertEqual(total_in_place + total_in_wallet_not_place, total_token_value)
        # Dans le cashles, on ne stocke pas les wallet du lieu :
        self.assertEqual(total_local_euro, total_in_wallet_not_place)

        # Asset CADEAU
        asset_local_gift_fedow = fedowAPI.asset.retrieve(f"{asset_g.pk}")

        total_token_value = asset_local_gift_fedow.get('total_token_value')
        total_in_place = asset_local_gift_fedow.get('total_in_place')
        total_in_wallet_not_place = asset_local_gift_fedow.get('total_in_wallet_not_place')

        self.assertEqual(total_in_place + total_in_wallet_not_place, total_token_value)
        self.assertEqual(total_gift, total_in_wallet_not_place)
        self.assertEqual(0, total_in_place)

    def ajout_monnaie_locale_post_fedow(self):
        recharge_local_euro_10: Articles = Articles.objects.get(
            name="+10",
            methode_choices=Articles.RECHARGE_EUROS,
        )

        self.assertIsInstance(recharge_local_euro_10, Articles)
        self.assertEqual(recharge_local_euro_10.prix, 10)
        self.assertFalse(recharge_local_euro_10.fractionne)
        self.assertFalse(recharge_local_euro_10.archive)

        primary_card = CarteMaitresse.objects.filter(
            points_de_vente__isnull=False,
            carte__isnull=False,
            carte__membre__isnull=False,
        ).first()

        responsable: Membre = primary_card.carte.membre

        # Ce point de vente doit être tout seul
        pdv = PointDeVente.objects.get(comportement=PointDeVente.CASHLESS)
        self.assertIsInstance(pdv, PointDeVente)

        carte = CarteCashless.objects.filter(
            membre__isnull=False,
            cartes_maitresses__isnull=True,
            assets__isnull=False,
        ).first()
        wallet = carte.wallet
        # On récupère l'asset pour vérifier que l'uuid soit le même sur le token fedow
        asset_local = carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_EURO)
        total_avant_recharge = asset_local.qty

        qty = 2
        total: Decimal = dround((recharge_local_euro_10.prix * qty))
        self.assertEqual(total, 20)

        json_achats = {"articles": [{"pk": str(recharge_local_euro_10.pk), "qty": qty}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": total,
                       "moyen_paiement": 'carte_bancaire',
                       "tag_id": carte.tag_id,
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        data_response = response.json()
        carte_in_response = data_response.get('carte')

        # Tout semble ok en db, le retrieve à bien écrasé la valeur
        if dround(carte_in_response['total_monnaie']) != dround(total_avant_recharge + total):
            import ipdb;
            ipdb.set_trace()

        self.assertEqual(dround(carte_in_response['total_monnaie']), dround(total_avant_recharge + total))
        carte.refresh_from_db()
        total_apres_recharge = carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_EURO).qty
        self.assertEqual(total_apres_recharge, dround(total_avant_recharge + total))

        # On check sur Fedow
        fedowAPI = FedowAPI()
        serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
        wallet_uuid = serialized_card['wallet']['uuid']
        self.assertEqual(wallet_uuid, wallet.uuid)
        tokens = {token['asset_uuid']: token['value'] for token in serialized_card['wallet']['tokens']}
        # la valeur correspond au Moyen de paiement ?
        self.assertEqual(tokens[asset_local.monnaie.pk], int((total_avant_recharge + total) * 100))
        tokens = {token['uuid']: token['value'] for token in serialized_card['wallet']['tokens']}
        # l'uuid du token est egal à l'asset cashless ?
        self.assertEqual(tokens[asset_local.pk], int((total_avant_recharge + total) * 100))

        # On check sur cashless :
        check_carte_data = {
            "tag_id_client": carte.tag_id,
        }
        check_response = self.client.post('/wv/check_carte',
                                          data=json.dumps(check_carte_data, cls=DjangoJSONEncoder),
                                          content_type="application/json",
                                          HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(check_response.status_code, 200)
        check_content = check_response.json()
        self.assertEqual(check_content.get('tag_id'), f"{carte.tag_id}")
        assets = {asset['monnaie']: asset['qty'] for asset in check_content.get('assets')}
        self.assertEqual(dround(assets[f"{asset_local.monnaie.pk}"]), dround(total_avant_recharge + total))

    def check_carte_fedow(self, carte):
        carte: CarteCashless = carte
        wallet = carte.wallet

        asset_local = carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_EURO)
        qty_avant_check_fedow = asset_local.qty

        # On check sur Fedow
        fedowAPI = FedowAPI()
        serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
        wallet_uuid = serialized_card['wallet']['uuid']
        self.assertEqual(wallet_uuid, wallet.uuid)
        tokens = {token['asset_uuid']: token['value'] for token in serialized_card['wallet']['tokens']}
        # la valeur correspond au Moyen de paiement ?
        self.assertEqual(tokens[asset_local.monnaie.pk], int(qty_avant_check_fedow * 100))
        tokens = {token['uuid']: token['value'] for token in serialized_card['wallet']['tokens']}
        # l'uuid du token est egal à l'asset cashless ?

        self.assertEqual(tokens[asset_local.pk], int(qty_avant_check_fedow * 100))

        # On check sur cashless :
        check_carte_data = {
            "tag_id_client": carte.tag_id,
        }
        check_response = self.client.post('/wv/check_carte',
                                          data=json.dumps(check_carte_data, cls=DjangoJSONEncoder),
                                          content_type="application/json",
                                          HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(check_response.status_code, 200)
        check_content = check_response.json()
        self.assertEqual(check_content.get('tag_id'), f"{carte.tag_id}")
        assets = {asset['monnaie']: asset['qty'] for asset in check_content.get('assets')}
        self.assertEqual(dround(assets[f"{asset_local.monnaie.pk}"]), dround(qty_avant_check_fedow))

        # On vérifie depuis la db que les assets correspondent
        carte.refresh_from_db()
        assets_from_db = carte.assets.all()
        for monnaie_uuid, qty in assets.items():
            asset_db = assets_from_db.get(monnaie__pk=monnaie_uuid)
            self.assertEqual((asset_db.qty), dround(qty))

        return serialized_card

    def checkout_stripe_from_fedow(self, id_event_checkout=None):
        # Lancer stripe :
        # stripe listen --forward-to http://127.0.0.1:8442/webhook_stripe/
        # S'assurer que la clé de signature soit la même que dans le .env
        carte = CarteCashless.objects.filter(membre__isnull=False, wallet__isnull=False).first()
        self.assertFalse(carte.assets.filter(monnaie__categorie=MoyenPaiement.STRIPE_FED).exists())
        membre = carte.membre
        email = membre.email
        fedowAPI = FedowAPI()
        checkout_url = fedowAPI.NFCcard.get_checkout(email=email, tag_id=carte.tag_id)
        self.assertIsInstance(checkout_url, str)
        self.assertIn('https://checkout.stripe.com/c/pay/cs_test', checkout_url)
        print('')
        print('Test du paiement. Lancez stripe cli avec :')
        print('stripe listen --forward-to http://127.0.0.1:8442/webhook_stripe/')
        print('pour relancer un event : stripe events resend <id>')
        print('')
        print('lancez le paiement avec 42€ et la carte 4242 :')
        print(f"{checkout_url}")
        print('')
        check_stripe = input("Une fois le paiement validé, 'entrée' pour tester le paiement réussi. NO pour passer :\n")
        serialized_card = self.check_carte_fedow(carte)
        if check_stripe != "NO":
            self.assertTrue(carte.assets.filter(monnaie__categorie=MoyenPaiement.STRIPE_FED).exists())
            self.assertEqual(carte.assets.get(monnaie__categorie=MoyenPaiement.STRIPE_FED).qty, Decimal(42))
            print("checkout verifié ! bravo :)")

    def add_me_to_test_fed(self):
        config = Configuration.get_solo()
        fedowApi = FedowAPI()
        accepted_assets = fedowApi.place.add_me_to_test_fed()

        # Les moyen de paiemenst on bien été créé par self.get_accepted_assets()
        # Si ça plante, c'est qu'ils n'ont pas été créé après le add_me_to_test_fed
        fiducial_assets = [MoyenPaiement.objects.get(pk=asset.get('uuid')) for asset in accepted_assets if
                           asset.get('category') == AssetValidator.TOKEN_LOCAL_FIAT]

    def check_federated_card_from_fedow(self):
        # On va tester une carte qui n'existe pas en DB,
        # mais qui existe coté fedow sur un autre lieux
        fedowAPI = FedowAPI()
        created = False
        config = Configuration.get_solo()
        try:
            fedow_card = fedowAPI.NFCcard.retrieve(user_card_firstTagId="ABCD1234")
            card = CarteCashless.objects.get(tag_id=fedow_card['first_tag_id'])
        except FileNotFoundError:
            print("Pas de carte avec le tag_id ABCD1234 chez Fedow, on la créé en on l'envoie")
            card = self.create_card(tag_id="ABCD1234")
            created = True
            # On la charge avec 10€ et 10 cadeau
            self.ajout_monnaie_bis(carte=card, qty=10)
            # on check
            self.check_carte_bis(carte=card, total=20)
            fedow_card = fedowAPI.NFCcard.retrieve(user_card_firstTagId="ABCD1234")
        except CarteCashless.DoesNotExist:
            import ipdb;
            ipdb.set_trace()

        self_origin = Origin.objects.get(place__name=f"{config.structure}", generation=1)
        self_place = Place.objects.get(name=f"{config.structure}")

        if not created:
            # La carte  n'pas été créée, cela veut dire qu'elle est d'une autre origin.
            self.assertTrue(len(Origin.objects.all()) > 1)
            self.assertNotEqual(card.origin, self_origin)
            # Doit être egal a dix car nous avons rechargé 10 € et 10 cadeau.
            # Seul les euros fédérés sont visible.
            self.assertEqual(card.total_monnaie(), Decimal(10.00))
            self.check_carte_bis(carte=card, total=10)
            # Check l'origine extérieure de l'asset
            self.assertEqual(card.assets.count(), 1)
            self.assertEqual(card.assets.get(monnaie__categorie=MoyenPaiement.EXTERIEUR_FED).qty, Decimal(10.00))
        else:
            # La carte a été créée, c'est le premier passage du test, on vérifie que l'origin existe
            self.assertTrue(len(Origin.objects.all()) == 1)
            self.assertEqual(card.origin, self_origin)
            # 20 car on compte ici les cadeaux et les euros
            self.check_carte_bis(carte=card, total=20)

        return card

    # ./manage.py test --tag=fast --tag=no-fedow
    @tag('no-fedow')
    def test_cashless(self):
        settings.FEDOW = False
        print("log user test to admin")
        log_admin = self.connect_admin()

        print("Création d'une boutique en base de donnée")
        self.pos_boutique = self.create_pos()

        print("Création de 20 cartes carshless dont 5 primaires")
        self.create_cards_with_db()

        print("Création de 5 membre avec carte primaire, 5 avec carte simple, 5 sans carte")
        self.member_with_card: Membre = self.create_members_with_db()

        print("Liaison d'une carte primaire au pos la boutique")
        self.primary_card = self.link_card_primary_to_pos()

        print("Création d'un article boisson, vente via api /wv/paieemnt en espèce et vente en carte bancaire")
        self.paiement_espece_carte_bancaire()

        print(
            "Création d'un article recharge cashless 10€, test d'une recharge sans carte nfc, test d'une recharge avec carte")
        self.carte_chargee = self.ajout_monnaie()

        print("Test de la route /wv/check_carte. Avec carte inexistante, carte avec membre, carte sans membre")
        self.check_carte()

        print("achat cashless avec carte NFC")
        self.paiement_cashless()

        print("Test paiement complémentaire avec deux cartes")
        self.paiement_complementaire_transactions()

        print('recharge de carte puis remboursement via le front')
        self.remboursement_front()

    # ./manage.py test --tag=fast --tag=fedow
    @tag('fedow')
    def test_fedow(self):
        # On relance les test précédents
        self.test_cashless()


        settings.FEDOW = True
        print('handshake avec serveur fedow')
        self.handshake_with_fedow_serveur()

        print(
            "AVEC FEDOW Création d'un article boisson, vente via api /wv/paieemnt en espèce et vente en carte bancaire")
        self.paiement_espece_carte_bancaire()

        print('création de la badgeuse')
        self.create_badgeuse()

        print("Envoi des assets euro, cadeau et adhésion à fedow")
        self.send_asset_to_fedow_with_api()

        print("Envoi de toute les cartes d'un coup vers fedow")
        self.send_card_to_fedow_with_api()

        print("Création d'un wallet fedow avec une carte et un email")
        self.creation_wallet_carte_vierge_et_email()

        print("Création d'un wallet fedow avec un email seul")
        self.creation_wallet_avec_email_seul()

        print("Meme user avec deux cartes différentes")
        self.same_membre_different_card()

        print("création d'un wallet avec une carte seule (ephemere)")
        self.creation_wallet_card_seule()

        print("Envoie des adhésions à fedow")
        self.send_adh_to_fedow_with_api()

        print("Récupération d'un wallet via le tag_id")
        self.serialized_card = self.fedow_wallet_with_tagid()

        print("Recharge d'une carte vierge (wallet ephemere) et d'une carte avec membre (wallet membre)")
        self.refill_card_wallet()

        print("Recharge d'un wallet user sans carte")
        self.refill_user_wallet()

        print("liaison d'une carte avec wallet ephemere à un user existant")
        self.link_wallet_ephemere_to_user()

        print("vente d'un article")
        transaction = self.user_to_place_transaction()

        print("remboursement et vidage d'une carte")
        self.remboursement_et_vidage_direct_api()

        print("add euro asset and gift asset and void")
        self.refill_and_void()

        print("Test paiement complémentaire avec deux cartes")
        self.paiement_complementaire_transactions()

        print("remboursement via front avec Fedow")
        self.remboursement_front()

        # print("Test de la route /wv/check_carte. Avec carte inexistante, carte avec membre, carte sans membre")
        # self.check_carte()

    # ./manage.py test --tag=fast --tag=stripe
    @tag('stripe')
    def test_posthandshake(self):
        settings.FEDOW = True
        self.handshake_with_fedow_serveur()

        # Connect
        self.connect_admin()
        # Fabrication de cartes
        self.create_cards_with_db()
        # Fabrication de membres
        self.create_members_with_db()
        # Ajout boutique et lien vers CM
        self.create_pos()
        self.link_card_primary_to_pos()
        self.create_badgeuse()

        # Ajoute des sous
        settings.FEDOW = False
        self.ajout_monnaie()

        settings.FEDOW = True
        # Envoie des assets, des cartes et des tokens déja existants.
        self.post_handshake()

        # On check que les tokens ont bien été envoyé
        self.check_all_tokens_value()

        # On ajoute des token locaux avec la webview
        self.ajout_monnaie_locale_post_fedow()

        # On check que la db fedow et la db cashless corresponde toujours
        self.check_all_tokens_value()

        # On lance un paiement cashless avec Fedow
        carte = self.paiement_cashless()

        # Correspondance entre fedow et cashless
        self.check_carte_fedow(carte)

        # On check que la db fedow et la db cashless corresponde toujours
        self.check_all_tokens_value()

        print("Test paiement complémentaire avec deux cartes")
        self.paiement_complementaire_transactions()

        # Tester le paiement stripe pour le rechargement, et le remboursement des euro seul ensuite
        self.checkout_stripe_from_fedow()
        self.remboursement_front_after_stripe_fed()

        self.add_me_to_test_fed()
        card = self.check_federated_card_from_fedow()
        self.paiement_cashless_external_token(card)

        # test avec des virgules
        self.paiement_cashless_virgule()

    def badge(self, carte=None):
        config = Configuration.get_solo()
        if not carte:
            carte = CarteCashless.objects.filter(membre__isnull=False).last()

        primary_card = CarteMaitresse.objects.first()
        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(name="Badgeuse")
        article: Articles = Articles.objects.get(methode_choices=Articles.BADGEUSE)

        # Solde insuffisant
        json_achats = {"articles": [{"pk": f"{article.pk}", "qty": 1}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": f"{0}",
                       "tag_id": f"{carte.tag_id}",
                       "moyen_paiement": 'nfc',
                       }

        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        av = ArticleVendu.objects.first()
        self.assertEqual(av.article, article)
        self.assertEqual(av.carte, carte)
        mp_badgeuse = MoyenPaiement.objects.get(categorie=MoyenPaiement.BADGE)
        self.assertEqual(av.moyen_paiement, mp_badgeuse)

    def badge_fedow(self, carte=None):
        config = Configuration.get_solo()
        if not carte:
            carte = CarteCashless.objects.filter(membre__isnull=False).last()

        primary_card = CarteMaitresse.objects.first()
        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(name="Badgeuse")
        article: Articles = Articles.objects.get(methode_choices=Articles.BADGEUSE)

        import ipdb;
        ipdb.set_trace()

    # ./manage.py test --tag=fast --tag=badge
    @tag('badge')
    def x_test_badgeuse(self):
        self.connect_admin()
        self.create_cards_with_db()
        self.create_members_with_db()
        self.create_pos()
        self.link_card_primary_to_pos()
        self.create_badgeuse()
        self.badge()

        settings.FEDOW = True
        self.handshake_with_fedow_serveur()
        self.post_handshake()
        self.add_me_to_test_fed()

        # On rebadge avec un asset exterieur
        self.badge_fedow()
        # tester refund et void -> toujours membership et badge

    def x_test_fidelity(self):
        # tester refund et void -> toujours fidelity
        pass

    def x_test_appariage(self):
        #TODO: Tester l'appairage avec discovery
        pass

# TEST TOUT :
# ./manage.py test && ./manage.py test --tag=stripe
