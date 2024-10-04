import time
from io import StringIO
from uuid import UUID

import requests
from OpenSSL.crypto import verify
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase, tag
from faker import Faker

from APIcashless.models import *
from fedow_connect.fedow_api import FedowAPI
from fedow_connect.validators import TransactionValidator, AssetValidator


class TiBilletTestCase(TestCase):

    def setUp(self):
        settings.DEBUG = True
        # Handshake avec le serveur FEDOW réalisé par install
        call_command('install', '--tdd', stdout=StringIO())


class CashlessTest(TiBilletTestCase):

    def check_handshake_with_fedow_serveur(self):
        # Réclamation d'une connexion a Fedow
        # session = requests.Session()
        # url = 'https://fedow.tibillet.localhost/get_new_place_token_for_test/'
        # request = session.get(url, verify=False, timeout=1)
        # string_fedow_connect = request.json().get('encoded_data')

        config: Configuration = Configuration.get_solo()
        fedowAPI = FedowAPI()
        settings.DEBUG = True

        # Le handshake se fait lors du set_up
        self.assertTrue(config.can_fedow())
        self.assertTrue(config.fedow_synced)

        get_accepted_assets = fedowAPI.place.get_accepted_assets()

        # Les adhésions et la badgeuse sont créé depuis LesPass
        # Trois assets ont été créé par le handshake avec Fedow
        # Trois assets créé par lespass : deux adhésion et un badge
        self.assertEqual(len(get_accepted_assets), 6)
        cats = [asset.get('category') for asset in get_accepted_assets]
        self.assertIn('FED', cats)
        self.assertIn('TNF', cats)
        self.assertIn('TLF', cats)
        self.assertIn('SUB', cats)
        self.assertIn('BDG', cats)

        badgeuse_tibilletistan = MoyenPaiement.objects.get(categorie=MoyenPaiement.EXTERNAL_BADGE)
        adhesions_tibilletistan = MoyenPaiement.objects.filter(categorie=MoyenPaiement.EXTERNAL_MEMBERSHIP)
        self.assertEqual(adhesions_tibilletistan.count(), 2)

        # Les adhesion et la badgeuse vient d'ailleurs
        tibilletistan = badgeuse_tibilletistan.place_origin
        self.assertIsInstance(tibilletistan, Place)
        for adhesion in adhesions_tibilletistan:
            self.assertEqual(adhesion.place_origin, tibilletistan)

        # On vérifie que les origines soient bien différentes
        local_euro = MoyenPaiement.get_local_euro()
        test_place = local_euro.place_origin
        self.assertIsInstance(test_place, Place)
        self.assertTrue(test_place != tibilletistan)

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
        self.assertInHTML('<input name="username" id="username" type="text" placeholder="username"/>',
                          response.content.decode())
        self.assertInHTML('<input name="password" id="password" type="password" placeholder="password"/>',
                          response.content.decode())

        # User ROOT
        rootuser = User.objects.create_superuser('rootuser', 'root@root.root', 'ROOTUSERPASSWORD')
        log = self.client.login(username='rootuser', password='ROOTUSERPASSWORD')
        self.assertTrue(log)

        # Le root est desormais redirigé vers adminstaff
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
        self.assertRedirects(response, '/adminstaff/', status_code=302, target_status_code=200)

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

        settings.DEBUG = True
        return True

    def created_pos(self):
        boutique = PointDeVente.objects.get(name="Boutique")
        return boutique

    #### ATOMIC UTILS FUNC FOR TEST #####

    def create_one_card_db(self, tag_id=None, number=None, qr_code=None):
        if not tag_id:
            tag_id = str(uuid4())[:8].upper()
        if not qr_code:
            qr_code = str(uuid4())
        if not number:
            number = qr_code[:8].upper()

        try:
            config = Configuration.get_solo()
            origin, created = Origin.objects.get_or_create(place__name=f"{config.structure}", generation=1)
        except Origin.DoesNotExist:
            origin = None

        carte = CarteCashless.objects.create(
            tag_id=f"{tag_id}",
            number=f"{number}",
            uuid_qrcode=f"{qr_code}",
            origin=origin,
        )

        carte.refresh_from_db()
        return carte

    def check_carte_total(self, carte, total) -> CarteCashless:
        response = self.client.post('/wv/check_carte',
                                    data=json.dumps({"tag_id_client": carte.tag_id}, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'popup_check_carte.html')
        self.assertNotContains(response, 'check-carte-inconnue')
        self.assertContains(response, 'check-carte-ok')

        self.assertContains(response, '<span>Tirelire</span>')

        str_total = "0" if total == 0 else f"{(int(total)):.2f}"
        self.assertContains(response, f'title="total">{str_total}</span>')

        carte.refresh_from_db()
        # Check la fonction interne total monnaie après un refresh from db
        self.assertEqual(carte.total_monnaie(), total)

        return carte

    def ajout_monnaie_bis(self, carte=None, qty=None):
        recharge_local_euro_1: Articles = Articles.objects.get(
            name="+1",
            methode_choices=Articles.RECHARGE_EUROS,
        )

        name_gift = "Cadeau +1" if settings.LANGUAGE_CODE == 'fr' else "Gift +1"
        recharge_local_gift_1: Articles = Articles.objects.get(
            name=name_gift,
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

    #### ATOMIC UTILS FUNC FOR TEST #####
    def create_20cards_5primary_with_db(self):
        cards, primary = [], []
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
                primary.append(carte_p)
            else:
                cards.append(carte_p)

        return cards, primary
        # self.assertEqual(CarteMaitresse.objects.filter(
        #     points_de_vente__isnull=True,
        #     carte__isnull=False).count(), 5)

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

        carte_m: CarteMaitresse = CarteMaitresse.objects.filter(
            points_de_vente__isnull=True,
            carte__membre__isnull=False).first()
        carte_m.points_de_vente.add(boutique)

        self.assertIn(carte_m, boutique.cartes_maitresses.all())

        return carte_m

    def user_terminal(self):
        User = get_user_model()

        appareil = Appareil.objects.create(name='testappareil_for_paiement')
        # On le met volontairement en staff pour tester que ça ne lui permette pas d'aller dans l'admin
        user_terminal = User.objects.create(
            username='user_terminal_paiement',
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

        log_user_terminal = self.client.login(username='user_terminal_paiement', password='PASSWORDTERMINAL')

        # Ne doit jamais pouvoir se logguer sur l'admin, en debug ou pas
        settings.DEBUG = False
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 405)
        settings.DEBUG = True
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 405)

        return user_terminal

    def paiement_espece_carte_bancaire(self):
        # point de vente créé par install --tdd
        pdv = PointDeVente.objects.get(name="Boutique")
        primary_card = pdv.cartes_maitresses.first()

        boisson: Articles = Articles.objects.create(
            name="Boisson_Test",
            prix=10,
            prix_achat="1",
            methode_choices=Articles.VENTE,
        )

        self.assertIsInstance(primary_card, CarteMaitresse)
        self.assertIsInstance(primary_card.carte, CarteCashless)
        responsable: Membre = primary_card.carte.membre
        self.assertIsInstance(responsable, Membre)

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

        # On test sans être loggué :
        settings.DEBUG = False
        self.client.logout()
        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                                    )
        # redirection vers login
        self.assertEqual(response.status_code, 302)

        # On se loggue avec un user terminal
        log_user_terminal = self.client.login(username='user_terminal_paiement', password='PASSWORDTERMINAL')
        settings.DEBUG = True
        response = self.client.post('/wv/paiement',
                                    data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                                    )

        if response.status_code != 200:
            # L'user est bien loggué en terminal ?
            import ipdb;
            ipdb.set_trace()

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

        # TEST avec carte avec wallet ephemère et token cadeau
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
        self.check_carte_total(carte, dround(ex_total_monnaie - total))

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
        primary_card = CarteMaitresse.objects.filter(
            carte__membre__isnull=False).first()
        responsable: Membre = primary_card.carte.membre
        self.assertIsInstance(responsable, Membre)

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

    def paiement_cashless_arg(self, carte, total):
        responsable = CarteMaitresse.objects.filter(
            carte__isnull=False,
            carte__membre__isnull=False,
        ).first().carte.membre

        boisson: Articles = Articles.objects.get_or_create(
            name="Article_test_1€",
            prix=1,
            prix_achat="1",
            methode_choices=Articles.VENTE,
        )[0]

        pdv = PointDeVente.objects.get_or_create(name="Boutique")[0]
        self.assertIsInstance(pdv, PointDeVente)

        total = dround(total)
        self.assertIsInstance(total, Decimal)
        qty = total
        total_transaction: Decimal = dround((boisson.prix * qty))
        self.assertEqual(total, total_transaction)
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
        self.assertIsNotNone(art_v.carte)
        self.assertEqual(art_v.carte, carte)

        carte.refresh_from_db()
        return carte

    def paiement_cashless(self):

        boisson: Articles = Articles.objects.create(
            name="Boisson_Test",
            prix=10,
            prix_achat="1",
            methode_choices=Articles.VENTE,
        )

        primary_card = CarteMaitresse.objects.filter(
            carte__membre__isnull=False).first()
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

    def check_carte_error(self):
        # Test sur carte qui n'existe pas
        check_carte_data = {
            "tag_id_client": "XXXXXXXX",
        }
        response = self.client.post('/wv/check_carte',
                                    data=json.dumps(check_carte_data, cls=DjangoJSONEncoder),
                                    content_type="application/json",
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'popup_check_carte.html')
        self.assertContains(response, 'check-carte-inconnue')
        self.assertNotContains(response, 'check-carte-ok')
        self.assertContains(response, '#e93363')  # couleur letchi

        # Test sur carte chargée :
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
        self.assertTemplateUsed(response, 'popup_check_carte.html')
        self.assertNotContains(response, 'check-carte-inconnue')
        self.assertContains(response, 'check-carte-ok')
        self.assertContains(response, '#b85521')  # couleur orange

    def send_card_to_fedow_with_api(self):
        cards = CarteCashless.objects.all()
        config = Configuration.get_solo()
        self.assertTrue(config.can_fedow())
        fedowAPI = FedowAPI()
        # Les cartes sont automatiquement envoyé à Fedow par un signal post_save
        # On check que Fedow renvoie bien un 409 : conflict, existe déja
        try:
            response = fedowAPI.NFCcard.create(cards)
        except Exception as e:
            self.assertIn('409', str(e))

    def creation_wallet_carte_vierge(self):
        # Les cartes n'ont pas de wallet, on check qu'ils sont créé avec l'envoie à Fedow
        fedowAPI = FedowAPI()
        carte = self.create_one_card_db()
        serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
        # fedowAPI a créé un wallet
        carte.refresh_from_db()
        self.assertIsInstance(carte.wallet, Wallet)
        self.assertEqual(serialized_card.get('wallet').get('uuid'), carte.wallet.uuid)
        self.assertTrue(serialized_card['is_wallet_ephemere'])

    def send_adh_to_fedow_with_api(self):
        # TODO: L'adhésion ne se fait plus avec le membre, mais avec le wallet
        # TEST AVEC WALLET SEUL
        # TEST AVEC WALLET QUI A DEJA SON EMAIL
        # Créer une adhésion sur lespass et vérifier ici

        # TODO: Tester avec une adhesion extérieure.
        # Erreur : Le token de l'adéhsion extérieur n'existe pas dans le wallet du lieu
        # Dans fedow, TokenNotFound avec un get()

        # D'abord, on test la validation d'une adhésion EXTERNE
        fedowAPI = FedowAPI()
        article_adhesion = Articles.objects.filter(
            methode_choices=Articles.ADHESIONS,
            subscription_fedow_asset__categorie=MoyenPaiement.ADHESION,
        ).first()

        """
        carte = membre.CarteCashless_Membre.first()
        wallet = carte.wallet or membre.wallet
        if not wallet:
            wallet: Wallet = fedowAPI.NFCcard.link_user(email=carte.membre.email, card=carte)

        adhesion = fedowAPI.subscription.create(
            wallet=f"{wallet.uuid}",
            amount=int(membre.cotisation * 100),
            date=membre.date_derniere_cotisation,
            user_card_firstTagId=carte.tag_id,
            article=article_adhesion,
        )

        self.assertIsInstance(adhesion, dict)
        self.assertEqual(adhesion.get('amount'), int(self.config.prix_adhesion * 100))
        self.assertEqual(adhesion.get('action'), TransactionValidator.SUBSCRIBE)
        self.assertEqual(adhesion.get('sender'), UUID(self.config.fedow_place_wallet_uuid))
        carte.refresh_from_db()
        self.assertEqual(adhesion.get('receiver'), carte.wallet.uuid)

        # TODO: vérifier le token uuid créé dans le cashless
        """

    def fedow_wallet_with_tagid(self):
        card = self.create_one_card_db()
        self.assertIsNotNone(card.tag_id)
        self.assertIsNotNone(card.uuid_qrcode)
        self.assertIsNotNone(card.number)

        fedowAPI = FedowAPI()
        serialized_card = fedowAPI.NFCcard.retrieve(card.tag_id)
        wallet = serialized_card.get('wallet')

        self.assertIsInstance(wallet, dict)
        self.assertIsInstance(wallet.get('uuid'), type(uuid4()))

        # Recharge de la base de donnée, le retrieve fedow fabrique et save la carte
        card.refresh_from_db()
        self.assertEqual(card.get_wallet().uuid, wallet.get('uuid'))

        data_for_laboutik = fedowAPI.card_wallet_to_laboutik(serialized_card)
        self.assertIsInstance(data_for_laboutik, dict)
        self.assertIsInstance(data_for_laboutik.get('total_monnaie'), Decimal)
        self.assertIsInstance(data_for_laboutik.get('assets'), list)
        self.assertEqual(data_for_laboutik.get('first_tag_id'), card.tag_id)

        return serialized_card

    def refill_card_wallet(self, carte=None, amount=4242):
        fedowAPI = FedowAPI()
        asset_local_euro = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        carte_primaire = CarteMaitresse.objects.first().carte

        if not carte:
            carte = self.create_one_card_db()
        # Le check carte va créer le wallet du coté de Fedow
        carte_avec_wallet_ephemere = self.check_carte_total(carte, 0)
        self.assertIsNotNone(carte_avec_wallet_ephemere.wallet)

        wallet: UUID = carte.get_wallet()
        self.assertIsInstance(wallet, Wallet)

        serialized_transaction = fedowAPI.transaction.refill_wallet(
            amount=amount,
            wallet=f"{wallet.uuid}",
            asset=f"{asset_local_euro.pk}",
            user_card_firstTagId=f"{carte.tag_id}",
            primary_card_fisrtTagId=carte_primaire.tag_id,
        )

        self.assertIsInstance(serialized_transaction, dict)
        self.assertEqual(serialized_transaction.get('amount'), amount)
        self.assertEqual(serialized_transaction.get('action'), TransactionValidator.REFILL)
        self.assertEqual(serialized_transaction.get('sender'), fedowAPI.config.fedow_place_wallet_uuid)
        self.assertEqual(serialized_transaction.get('receiver'), wallet.uuid)
        self.assertEqual(serialized_transaction.get('card')['first_tag_id'], carte.tag_id)
        self.assertEqual(serialized_transaction.get('primary_card'), carte_primaire.pk)
        self.assertIsNotNone(serialized_transaction.get('verify_hash'))

        # Vérification avec le retrieve
        serialized_card = fedowAPI.NFCcard.retrieve(f"{carte.tag_id}")
        self.assertIsInstance(serialized_card['wallet']['tokens'], list)
        tokens = [(token['asset_uuid'], token['value']) for token in serialized_card['wallet']['tokens']]
        self.assertIn((asset_local_euro.pk, amount), tokens)

        self.assertTrue(serialized_card.get('is_wallet_ephemere'))

        # tester que l'asset interne est bien a jour
        self.assertEqual(Assets.objects.get(carte=carte, monnaie=asset_local_euro).qty, dround(amount / 100))
        self.assertEqual(carte.total_monnaie(), dround(amount / 100))

        return carte

    def refill_user_wallet_without_card_test_error(self):
        fedowAPI = FedowAPI()
        asset_local_euro = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)

        # Création d'un nouveau wallet tout neuf en une ligne !
        new_wallet = self.check_carte_total(self.create_one_card_db(), 0).wallet

        serialized_transaction = fedowAPI.transaction.refill_wallet(
            amount=4242,
            wallet=f"{new_wallet.uuid}",
            asset=f"{asset_local_euro.pk}",
        )
        # Pas de carte ni de carte primaire : Indispensable pour un refill
        self.assertEqual(serialized_transaction, 400)

    def card_to_place_transaction_with_api_fedow(self):
        fedowAPI = FedowAPI()
        asset_local_euro = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)

        carte: CarteCashless = self.create_one_card_db()

        # 50 cadeau + 50 euro = 100
        self.ajout_monnaie_bis(carte=carte, qty=50)
        carte = self.check_carte_total(carte, 100)

        wallet = carte.wallet
        first_tag_id = carte.tag_id
        carte_primaire = CarteMaitresse.objects.first().carte

        serialized_transaction_w2w = fedowAPI.transaction.to_place(
            amount=2121,
            wallet=f"{wallet.uuid}",
            asset=f"{asset_local_euro.pk}",
            user_card_firstTagId=first_tag_id,
            primary_card_fisrtTagId=carte_primaire.tag_id,
        )

        self.assertIsInstance(serialized_transaction_w2w, dict)
        self.assertEqual(serialized_transaction_w2w.get('amount'), 2121)
        self.assertEqual(serialized_transaction_w2w.get('action'), TransactionValidator.SALE)
        self.assertEqual(serialized_transaction_w2w.get('receiver'), fedowAPI.config.fedow_place_wallet_uuid)
        self.assertEqual(serialized_transaction_w2w.get('sender'), wallet.uuid)
        self.assertEqual(serialized_transaction_w2w.get('card')['first_tag_id'], first_tag_id)
        self.assertEqual(serialized_transaction_w2w.get('primary_card'), carte_primaire.pk)
        self.assertIsNotNone(serialized_transaction_w2w.get('verify_hash'))

        asset = Assets.objects.get(carte=carte, monnaie=asset_local_euro.pk)

        # On va chercher le token dans le serialiser de la card post paiement et vérifier la quantité restante
        tokens = serialized_transaction_w2w['card']['wallet']['tokens']
        token_asset_local_euro = {}
        for token in tokens:
            if token['asset']['uuid'] == asset.monnaie.pk:
                token_asset_local_euro = token
        self.assertIsNotNone(token_asset_local_euro)
        self.assertEqual(token_asset_local_euro['value'], dround(50 - 21.21) * 100)

        # TODO: Checker une carte non authorisé (get_authority_delegation)

        return serialized_transaction_w2w

    def remboursement_front(self):
        config = Configuration.get_solo()
        primary_card = CarteMaitresse.objects.filter(
            carte__membre__isnull=False
        ).first()

        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(name="Boutique")
        carte, carte_bis = self.create_2_card_and_charge_it()

        self.check_carte_total(carte=carte, total=10)

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
        self.assertEqual(content.get('total_sur_carte_avant_achats'), f"10.00")
        # A rembourser = 5
        self.assertEqual(content.get('somme_totale'), f"5.00")

        self.check_carte_total(carte=carte, total=0)
        art_v = ArticleVendu.objects.first()
        self.assertEqual(art_v.moyen_paiement.categorie, MoyenPaiement.CASH)
        self.assertEqual(art_v.total(), Decimal(-5.00))

    def remboursement_front_after_stripe_fed(self, carte):
        ex_total_monnaie = carte.total_monnaie()

        self.assertTrue(ex_total_monnaie >= 42)
        self.check_carte_total(carte=carte, total=ex_total_monnaie)

        # On rajoute local euro et local cadeau pour pouvoir les vider ensuite
        self.ajout_monnaie_bis(carte=carte, qty=5)  # 5 cadeau + 5 local
        self.check_carte_total(carte=carte, total=ex_total_monnaie + 10)

        ex_total_asset_euro = carte.assets.get(monnaie__categorie=MoyenPaiement.LOCAL_EURO).qty
        self.assertTrue(ex_total_asset_euro >= 5)
        ex_total_asset_fed = carte.assets.get(monnaie__categorie=MoyenPaiement.STRIPE_FED).qty
        self.assertTrue(ex_total_asset_fed == 42)
        ex_total_a_rembourser = ex_total_asset_euro + ex_total_asset_fed

        #### PREPARATION DE LA REQUETE
        article_vider_carte: Articles = Articles.objects.get(
            methode_choices=Articles.VIDER_CARTE,
        )
        responsable = CarteMaitresse.objects.filter(
            carte__isnull=False,
            carte__membre__isnull=False,
        ).first().carte.membre

        pdv = PointDeVente.objects.get(comportement=PointDeVente.CASHLESS)

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
        # Fédéré remboursé :
        self.assertEqual(carte.assets.get(monnaie__categorie=MoyenPaiement.STRIPE_FED).qty, 0)

        # A rembourser = uniquement les assets locaux euro
        self.assertEqual(content.get('somme_totale'), f"{ex_total_a_rembourser}")

        # On a bien remboursé en espèce :
        art_v = ArticleVendu.objects.first()
        self.assertEqual(art_v.moyen_paiement.categorie, MoyenPaiement.CASH)

        self.assertEqual(art_v.total(), Decimal(-(ex_total_a_rembourser)))
        self.check_carte_total(carte=carte, total=0)

    def remboursement_et_vidage_direct_api(self):
        fedowAPI = FedowAPI()
        carte_primaire = CarteMaitresse.objects.first().carte

        # On fabrique une carte et on la charge :
        carte = self.create_one_card_db()
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

        # Création d'une nouveau carte tout neuf en une ligne !
        carte = self.check_carte_total(self.create_one_card_db(), 0)

        # On la charge de 10 + 10 gift
        self.ajout_monnaie_bis(carte=carte, qty=10)

        # TODO: a sortir d'ici -> atomic !
        ex_total_euro = carte.total_monnaie(carte.assets.filter(monnaie=MoyenPaiement.get_local_euro()))
        ex_total_gift = carte.total_monnaie(carte.assets.filter(monnaie=MoyenPaiement.get_local_gift()))
        self.assertEqual(ex_total_euro, 10)
        self.assertEqual(ex_total_euro, ex_total_gift)

        wallet: Wallet = carte.get_wallet()
        self.assertIsInstance(wallet, Wallet)

        ex_new_serialized_card = fedowAPI.NFCcard.retrieve(carte.tag_id)
        tokens = ex_new_serialized_card['wallet']['tokens']
        self.assertTrue(len(tokens) >= 2)

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
        self.assertEqual(serialized_transactions_voided[0].get('amount'), ex_total_euro * 100)
        self.assertEqual(serialized_transactions_voided[0].get('action'), TransactionValidator.REFUND)
        self.assertTrue(serialized_transactions_voided[0].get('verify_hash'))
        self.assertEqual(serialized_transactions_voided[1].get('amount'), ex_total_gift * 100)
        self.assertEqual(serialized_transactions_voided[1].get('action'), TransactionValidator.REFUND)
        self.assertTrue(serialized_transactions_voided[1].get('verify_hash'))

        # Checker que le void a retiré aussi le wallet du membre cashless
        carte.refresh_from_db()
        self.assertNotEqual(ex_new_serialized_card['wallet']['uuid'], carte.wallet.uuid)

        serialized_card_voided = new_void_data['serialized_card']
        self.assertEqual(serialized_card_voided['wallet']['tokens'], [])
        self.assertTrue(serialized_card_voided['is_wallet_ephemere'])

        # L'ancien wallet existe toujours, mais il est vide
        wallet_empty = fedowAPI.wallet.retrieve(f"{wallet.uuid}")
        after_void_token_dict = {token['asset_uuid']: token['value'] for token in wallet_empty['tokens']}
        self.assertEqual(after_void_token_dict[asset_local_euro.pk], 0)
        self.assertEqual(after_void_token_dict[asset_gift.pk], 0)

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

        self.assertTrue(config.can_fedow())
        fedowAPI = FedowAPI()
        # Les cartes sont automatiquement envoyé à Fedow par un signal post_save
        # On check que Fedow renvoie bien un 409 : conflict, existe déja
        try:
            response = fedowAPI.NFCcard.create(cartes)
        except Exception as e:
            self.assertIn('409', str(e))

        # Chargement des cartes
        for carte in cartes:
            self.ajout_monnaie_bis(carte=carte, qty=5)
            self.check_carte_total(carte=carte, total=10)

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
        asserted_message = 'Fonds insuffisants sur deuxieme carte.' if settings.LANGUAGE_CODE == 'fr' else 'Insufficient funds on second card.'
        self.assertEqual(message.get('msg'), asserted_message)
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
        self.check_carte_total(carte=carte, total=0)
        self.check_carte_total(carte=carte_bis, total=(total_complementaire - total))

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
        # asset_b = MoyenPaiement.objects.get(categorie=MoyenPaiement.BADGE)
        # asset_b.name = f"BADGE_{config.structure}"
        # asset_b.save()

        asset_e = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
        asset_e.name = f"EURO_{config.structure}"
        asset_e.save()
        asset_g = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)
        asset_g.name = f"CADEAU_{config.structure}"
        asset_g.save()

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

        # On check sur cashless :
        self.check_carte_total(carte, total_avant_recharge + total)

    def link_email_with_wallet_on_lespass(self, card=None, email=None):
        fedowAPI = FedowAPI()
        if not card:
            # Création d'une nouvelle carte et check carte pour récupérer le wallet
            card = self.create_one_card_db()
        if not email:
            email = Faker().email()

        # La carte est sensé être ephemère
        before_link_serialized_card = fedowAPI.NFCcard.retrieve(card.tag_id)
        self.assertTrue(before_link_serialized_card['is_wallet_ephemere'])

        config = Configuration.get_solo()
        lespass_link = requests.post(
            f"{config.billetterie_url}qr/link/",
            # Renvoie un redirect referer si erreur
            headers={'referer': 'https://laboutik.tibillet.localhost/test/'},
            data={
                'email': email,
                'cgu': True,
                'qrcode_uuid': f"{card.uuid_qrcode}"
            },
            verify=False,
        )
        self.assertEqual(lespass_link.status_code, 200)

        # On vérifie sur Fedow que la card n'est plus ephémère :
        serialized_card = fedowAPI.NFCcard.retrieve(card.tag_id)
        self.assertFalse(serialized_card['is_wallet_ephemere'])
        # Le wallet de la carte a changé après la fusion :
        self.assertNotEqual(before_link_serialized_card['wallet']['uuid'], serialized_card['wallet']['uuid'])

        # On test la page my_account de lespass :
        my_account = requests.get(f"{config.billetterie_url}qr/{card.uuid_qrcode}", verify=False)
        if my_account.status_code != 200:
            import ipdb;
            ipdb.set_trace()
        self.assertEqual(my_account.status_code, 200)

        return email, card

    def checkout_stripe_from_fedow_thru_lespass(self, carte):
        # Lancer stripe :
        # stripe listen --forward-to https://fedow.tibillet.localhost/webhook_stripe/ --skip-verify
        # S'assurer que la clé de signature soit la même que dans le .env

        # Token fédéré n'existe pas encore sur la carte
        self.assertFalse(carte.assets.filter(monnaie__categorie=MoyenPaiement.STRIPE_FED).exists())

        # On se connecte à Lespass :
        session = requests.session()
        config = Configuration.get_solo()
        # On se connecte sur lespass avec le scan qrcode qui loggue l'user automatiquement
        session.get(f"{config.billetterie_url}qr/{carte.uuid_qrcode}", verify=False)
        # On fait comme si on cliquais sur le bouton "recharger mon portefeuille"
        get_stripe_checkout = session.get(f"{config.billetterie_url}my_account/refill_wallet", verify=False)
        # Lespass utilise Hx-redirect :
        checkout_url = get_stripe_checkout.headers.get('Hx-Redirect')
        session.close()

        # Check stripe checkout link
        if type(checkout_url) != str:
            import ipdb;
            ipdb.set_trace()
        self.assertIsInstance(checkout_url, str)
        self.assertIn('https://checkout.stripe.com/c/pay/cs_test', checkout_url)
        print('')
        print('Test du paiement. Lancez stripe cli avec :')
        print('stripe listen --forward-to https://fedow.tibillet.localhost/webhook_stripe/ --skip-verify')
        print('pour relancer un event : stripe events resend <id>')
        print('')
        print('lancez le paiement avec 42€ et la carte 4242 :')
        print(f"{checkout_url}")
        print('')
        check_stripe = input("Une fois le paiement validé, 'entrée' pour tester le paiement réussi. NO pour passer :\n")

        if check_stripe != "NO":
            # Check cart pour refresh from fedow
            response = self.client.post('/wv/check_carte',
                                        data=json.dumps({"tag_id_client": carte.tag_id}, cls=DjangoJSONEncoder),
                                        content_type="application/json",
                                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')

            carte.refresh_from_db()
            self.assertTrue(carte.assets.filter(monnaie__categorie=MoyenPaiement.STRIPE_FED).exists())
            if carte.assets.get(monnaie__categorie=MoyenPaiement.STRIPE_FED).qty != Decimal(42):
                import ipdb;
                ipdb.set_trace()
            self.assertEqual(carte.assets.get(monnaie__categorie=MoyenPaiement.STRIPE_FED).qty, Decimal(42))

            print("checkout verifié & Paiement non vérifié")
        else:
            logger.warning("Paiement non vérifié")
            print("Paiement non vérifié")

    def add_me_to_test_fed(self):
        # En setting TEST, Fedow ajoute automatiquement
        # le nouveau place créé par le handshake dans une fédération de test
        fedowApi = FedowAPI()
        accepted_assets = fedowApi.place.get_accepted_assets()

        # TODO: Tester si déja dans monnaies acceptés ?
        import ipdb;
        ipdb.set_trace()
        fiducial_assets = [MoyenPaiement.objects.get(pk=asset.get('uuid')) for asset in accepted_assets if
                           asset.get('category') == AssetValidator.TOKEN_LOCAL_FIAT]
        config = Configuration.get_solo()
        config.monnaies_acceptes.add(*fiducial_assets)

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
            self.check_carte_total(carte=card, total=20)
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
            self.check_carte_total(carte=card, total=10)
            # Check l'origine extérieure de l'asset
            self.assertEqual(card.assets.count(), 1)
            self.assertEqual(card.assets.get(monnaie__categorie=MoyenPaiement.EXTERIEUR_FED).qty, Decimal(10.00))
        else:
            # La carte a été créée, c'est le premier passage du test, on vérifie que l'origin existe
            self.assertTrue(len(Origin.objects.all()) == 1)
            self.assertEqual(card.origin, self_origin)
            # 20 car on compte ici les cadeaux et les euros
            self.check_carte_total(carte=card, total=20)

        return card

    def retour_consigne(self):
        # Création d'une nouvelle carte et check carte pour récupérer le wallet
        carte = self.create_one_card_db()

        primary_card = CarteMaitresse.objects.filter(carte__isnull=False, carte__membre__isnull=False).first()
        responsable: Membre = primary_card.carte.membre
        pdv = PointDeVente.objects.get(comportement=PointDeVente.CASHLESS)

        article: Articles = Articles.objects.filter(methode_choices=Articles.RETOUR_CONSIGNE)[0]
        self.assertEqual(article.prix, -1)

        # Retour espèce
        json_achats = {"articles": [{"pk": f"{article.pk}", "qty": 3}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": 3,
                       "moyen_paiement": 'espece',
                       }

        response_cash = self.client.post('/wv/paiement',
                                         data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                         content_type="application/json",
                                         HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response_cash.status_code, 200)

        av = ArticleVendu.objects.first()
        self.assertEqual(av.article, article)
        self.assertEqual(av.total(), Decimal(-3))
        self.assertEqual(av.moyen_paiement.categorie, MoyenPaiement.CASH)

        # Retour NFC
        json_achats = {"articles": [{"pk": f"{article.pk}", "qty": 6}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": 6,
                       "tag_id": f"{carte.tag_id}",
                       "moyen_paiement": 'nfc',
                       }

        response_nfc = self.client.post('/wv/paiement',
                                        data=json.dumps(json_achats, cls=DjangoJSONEncoder),
                                        content_type="application/json",
                                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response_nfc.status_code, 200)

        av = ArticleVendu.objects.first()
        self.assertEqual(av.article, article)
        self.assertEqual(av.total(), Decimal(-6))
        self.assertEqual(av.moyen_paiement.categorie, MoyenPaiement.LOCAL_EURO)

        self.check_carte_total(carte=carte, total=6)
        carte.refresh_from_db()
        self.assertEqual(carte.total_monnaie(), Decimal(6))

    def remboursement_online_after_stripe_fed(self):
        email, carte = self.link_email_with_wallet_on_lespass()
        self.checkout_stripe_from_fedow_thru_lespass(carte)
        self.check_carte_total(carte, 42)
        self.paiement_cashless_arg(carte, 10)

        art_v: ArticleVendu = ArticleVendu.objects.first()
        self.assertEqual(art_v.moyen_paiement.categorie, MoyenPaiement.STRIPE_FED)

        self.check_carte_total(carte, 32)

        # On se connecte à Lespass :
        session = requests.session()
        config = Configuration.get_solo()
        # On se connecte sur lespass avec le scan qrcode qui loggue l'user automatiquement
        session.get(f"{config.billetterie_url}qr/{carte.uuid_qrcode}", verify=False)
        # On fait comme si on cliquais sur le bouton "recharger mon portefeuille"
        refund_response = session.get(f"{config.billetterie_url}my_account/refund_online", verify=False)
        session.close()

        # La carte a été vidée, elle est à zero
        self.check_carte_total(carte, 0)

        # TODO :Checker dashboard fedow :
        # import ipdb;
        # ipdb.set_trace()
        # https://fedow.tibillet.localhost/dashboard/asset/d85124bc-3c98-4928-9612-690cef2d46ba/

    def badge(self, carte=None):
        if not carte:
            email, carte = self.link_email_with_wallet_on_lespass()

        responsable: Membre = CarteMaitresse.objects.filter(carte__isnull=False,
                                                            carte__membre__isnull=False).first().carte.membre
        pdv = PointDeVente.objects.get(name="Adhésions")
        article: Articles = Articles.objects.get(methode_choices=Articles.BADGEUSE)
        self.assertTrue(article.subscription_fedow_asset)
        self.assertIsInstance(article.subscription_fedow_asset, MoyenPaiement)

        # Solde insuffisant
        json_achats = {"articles": [{"pk": f"{article.pk}", "qty": 1}],
                       "pk_responsable": f"{responsable.pk}",
                       "pk_pdv": f"{pdv.pk}",
                       "total": 0,
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
        # Le moyen de paiement est l'asset badgeuse
        self.assertEqual(av.moyen_paiement, article.subscription_fedow_asset)

        #TODO: tester badge sur dashboard fedow
        import ipdb;
        ipdb.set_trace()

    @tag('fedow')
    def test_fedow(self):
        print("log user test to admin")
        log_admin = self.connect_admin()

        print("Création d'un user terminal et log in avec")
        self.user_terminal()

        print("Création d'une boutique en base de donnée")
        self.pos_boutique = self.created_pos()

        print("Création de 20 cartes carshless dont 5 primaires")
        self.create_20cards_5primary_with_db()

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
        self.check_carte_error()

        print("achat cashless avec carte NFC")
        self.paiement_cashless()

        print("Test paiement complémentaire avec deux cartes")
        self.paiement_complementaire_transactions()

        print('recharge de carte puis remboursement via le front')
        self.remboursement_front()

        # END EX TEST TIBILLET SANS FEDOW

        print('handshake avec serveur fedow')
        self.check_handshake_with_fedow_serveur()

        print("Création de 20 cartes carshless dont 5 primaires")
        self.create_20cards_5primary_with_db()

        print(
            "AVEC FEDOW Création d'un article boisson, vente via api /wv/paiement en espèce et vente en carte bancaire")
        self.paiement_espece_carte_bancaire()

        print("Envoi de toute les cartes d'un coup vers fedow")
        self.send_card_to_fedow_with_api()

        print("création d'un wallet avec une carte seule (ephemere)")
        self.creation_wallet_carte_vierge()

        print("Envoie des adhésions à fedow")
        self.send_adh_to_fedow_with_api()

        print("Récupération d'un wallet via le tag_id")
        self.serialized_card = self.fedow_wallet_with_tagid()

        print("Recharge d'une carte vierge (wallet ephemere)")
        self.refill_card_wallet()

        print("Recharge d'un wallet user sans carte = Erreur !")
        self.refill_user_wallet_without_card_test_error()

        print("vente d'un article")
        self.card_to_place_transaction_with_api_fedow()

        print("remboursement et vidage d'une carte")
        self.remboursement_et_vidage_direct_api()

        print("add euro asset and gift asset and void")
        self.refill_and_void()

        print("Test paiement complémentaire avec deux cartes")
        self.paiement_complementaire_transactions()

        print("remboursement via front avec Fedow")
        self.remboursement_front()

        # On ajoute des token locaux avec la webview
        self.ajout_monnaie_locale_post_fedow()

        print("On check que la db fedow et la db cashless corresponde toujours")
        self.check_all_tokens_value()

        # test avec des virgules
        self.paiement_cashless_virgule()

        ### Retour Consigne
        self.retour_consigne()

        ### LINK TEST
        print("Création d'une carte vierge et liaison avec nouvel email")
        email, carte = self.link_email_with_wallet_on_lespass()
        print("Carte ephemère et déja chargée, liaison avec nouvel email, vérification que la fusion de wallet est ok")
        # create and refill card
        carte = self.refill_card_wallet(amount=6600)
        email, carte = self.link_email_with_wallet_on_lespass(card=carte)
        self.check_carte_total(carte, 66)

        ### STRIPE CHARGE TEST
        # print("Tester le paiement stripe pour le rechargement, et le remboursement sur place.")
        # self.checkout_stripe_from_fedow_thru_lespass(carte)
        # self.check_carte_total(carte, 66 + 42)
        # self.remboursement_front_after_stripe_fed(carte)

        #### STRIPE REFUND
        # A activer lorsqu'il y aura le remboursement
        # self.remboursement_online_after_stripe_fed()

        # TODO: moteur de lecture du dashboard
        logger.info("TEST OK. Pensez à vérifier : ")
        logger.info("- Sur le dashboard fedow, le place wallet doit être positif (42)")
        # TODO:Tester la carte perdue : elle doit etre bien vide

        # TODO: tester la carte perdue : si on en associe une autre, vérifier que les token existent toujours

        ### FEDERATION TEST
        # self.add_me_to_test_fed()

        # card = self.check_federated_card_from_fedow()
        # self.paiement_cashless_external_token(card)

        ### BADGE
        self.badge()
        # On rebadge avec un asset exterieur
        # self.badge_fedow()
        # tester refund et void -> toujours membership et badge

    def x_test_fidelity(self):
        # tester refund et void -> toujours fidelity
        pass

    def x_test_appariage(self):
        # TODO: Tester l'appairage avec discovery
        pass

# TEST TOUT :
# ./manage.py test && ./manage.py test --tag=stripe
