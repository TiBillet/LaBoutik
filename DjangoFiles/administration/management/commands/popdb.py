import json
import logging
import random
import socket
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand

from APIcashless.custom_utils import badgeuse_creation, declaration_to_discovery_server
from APIcashless.models import *

logger = logging.getLogger(__name__)


# TODO: rajouter les carte depuis le .env DEMO

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--flush',
                            action='store_true',
                            help='Flush la base de donnée')

        parser.add_argument('--test',
                            action='store_true',
                            help='Objects pour test front')

    def handle(self, *args, **options):


        class Lieu(object):
            """docstring for Lieu"""

            def __init__(self, options):
                self.nom_monnaie = os.environ.get('NOM_MONNAIE')
                if self.nom_monnaie:
                    self.monnaie_blockchain = self._monnaie_blockchain()

                self.moyens_de_paiements_non_blockchain = self._moyens_de_paiements_non_blockchain()

                self.methode_articles = self._methode_articles()
                self.configuration = self._configuration()

                self.couleur = self._couleur()

                self.articles_generiques = self._articles_generiques()
                self.pdv_cashless = self._point_de_vente_cashless()

                #TODO: On utilise l'email de l'admin dans le .env
                # self.users = self._user_admin()

                if options.get('test'):
                    self.pop_membre_articles_cartes_test()
                    self.pop_articles_test()
                    self.pop_tables_test()
                    self.preparation_test()
                    self.printer_test()
                    self.config_test()
                    badgeuse_creation()


            def _monnaie_blockchain(self):
                mp = {}
                mp['principale'] = MoyenPaiement.objects.get_or_create(name=self.nom_monnaie,
                                                                       blockchain=True,
                                                                       categorie=MoyenPaiement.LOCAL_EURO,
                                                                       )[0]

                mp['cadeau'] = MoyenPaiement.objects.get_or_create(name=f"{self.nom_monnaie} Cadeau",
                                                                   cadeau=True,
                                                                   blockchain=True,
                                                                   categorie=MoyenPaiement.LOCAL_GIFT,
                                                                   )[0]

                return mp

            def _moyens_de_paiements_non_blockchain(self):
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
                d['adhesion'] = Methode.objects.get_or_create(name="Adhesion")[0]
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
                configuration.domaine_cashless = settings.CASHLESS_URL

                # configuration.prix_adhesion = self.prix_adhesion

                configuration.monnaie_principale = self.monnaie_blockchain.get('principale')
                configuration.monnaie_principale_cadeau = self.monnaie_blockchain.get('cadeau')
                configuration.moyen_paiement_espece = self.moyens_de_paiements_non_blockchain.get('espece')
                configuration.moyen_paiement_cb = self.moyens_de_paiements_non_blockchain.get('carte_bancaire')
                configuration.moyen_paiement_mollie = self.moyens_de_paiements_non_blockchain.get('stripe')
                configuration.moyen_paiement_oceco = self.moyens_de_paiements_non_blockchain.get('oceco')
                configuration.moyen_paiement_commande = self.moyens_de_paiements_non_blockchain.get('commande')

                # Pour PkResponsable Web :
                Cashless, created = PointDeVente.objects.get_or_create(
                    name="Cashless",
                    icon="fa-euro-sign",
                    comportement='C',
                    accepte_commandes=False,
                    service_direct=True,
                    poid_liste=200,
                )
                Membre.objects.get_or_create(name="WEB STRIPE")

                try:
                    for key, monnaie in self.monnaie_blockchain.items():
                        configuration.monnaies_acceptes.add(monnaie)
                except Exception as e:
                    print(e)
                    import ipdb;
                    ipdb.set_trace()

                configuration.monnaies_acceptes.add(
                    configuration.monnaie_principale,
                    configuration.monnaie_principale_cadeau,
                )

                configuration.methode_vente_article = self.methode_articles.get('vente_article')
                configuration.methode_ajout_monnaie_virtuelle = self.methode_articles.get('ajout_monnaie_virtuelle')
                configuration.methode_ajout_monnaie_virtuelle = self.methode_articles.get(
                    'ajout_monnaie_virtuelle_cadeau')
                configuration.methode_adhesion = self.methode_articles.get('adhesion')
                configuration.methode_retour_consigne = self.methode_articles.get('retour_consigne')
                configuration.methode_vider_carte = self.methode_articles.get('vider_carte')
                configuration.methode_paiement_fractionne = self.methode_articles.get('paiement_fractionne')

                # configuration.emplacement = self.data.get("nom_monnaie")

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
                Cashless = PointDeVente.objects.get(
                    comportement='C'
                )

                for key, art in self.articles_generiques.items():
                    Cashless.articles.add(art) if art not in Cashless.articles.all() else art

                return Cashless

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


            """
            def _user_admin(self):
                User = get_user_model()

                root, created = User.objects.get_or_create(username=self.data.get('root_login'))
                if created:
                    root.set_password(self.data.get('root_password'))
                    root.is_superuser = True
                    root.is_staff = True
                    root.is_superstaff = True
                    root.save()

                staff_group, created = Group.objects.get_or_create(name="staff")

                staff, created = User.objects.get_or_create(username=self.data.get('staff_login'))
                if created:
                    staff.set_password(self.data.get('staff_password'))
                    staff.is_staff = True
                    staff.is_superstaff = True
                    staff.groups.add(staff_group)
                    staff.save()

                # creation de l'user qui ne peux que créer des membres :
                creationMembre, created = User.objects.get_or_create(username=self.data.get('membre_login'))
                if created:
                    creationMembre.set_password(self.data.get('membre_password'))
                    creationMembre.is_staff = True
                    creationMembre.save()

                creationMembre_group, created = creationMembre.groups.get_or_create(name="creationMembre")

                # on clean les permissions :
                call_command('check_permissions')
            """

            def pop_membre_articles_cartes_test(self):
                try:
                    testMembre, created = Membre.objects.get_or_create(name="TEST",
                                                                       email="test@example.org",
                                                                       cotisation=0)
                except Exception as e:
                    testMembre = Membre.objects.get(name="TEST")
                    pass

                try:
                    jonas_membre, created = Membre.objects.get_or_create(name="JONAS",
                                                                         email="jonas@billetistan.coop",
                                                                         cotisation=0)
                except Exception as e:
                    jonas_membre = Membre.objects.get(name="JONAS")
                    pass

                try:
                    robocop_membre, created = Membre.objects.get_or_create(name="ROBOCOP",
                                                                           cotisation=0)
                except Exception as e:
                    robocop_membre = Membre.objects.get(name="ROBOCOP")
                    pass

                try:
                    framboise_membre, created = Membre.objects.get_or_create(name="FRAMBOISIÉ",
                                                                             cotisation=0)
                except Exception as e:
                    framboise_membre = Membre.objects.get(name="FRAMBOISIÉ")
                    pass

                try:
                    mike_membre, created = Membre.objects.get_or_create(name="Mike",
                                                                        email="mike@billetistant.coop",
                                                                        cotisation=100)
                except Exception as e:
                    mike_membre = Membre.objects.get(name="Mike")
                    pass

                origin = Origin.objects.get_or_create(generation=1)[0]

                cards = []
                # pour cashless_test1
                if os.environ.get('NOM_MONNAIE') == 'TestCoin':
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
                        ["https://m.tibillet.re/qr/58515F52-747b-4934-93f2-597449bcde22", "58515F52", "C42BC42A"],
                    ]
                else:
                    # Pour cashless_test2
                    cards = [
                        ["https://demo.tibillet.localhost/qr/81fd9485-c806-4991-adf8-6cb44ee5e6d1", "81FD9485",
                         "6172BACA"],
                        ["https://demo.tibillet.localhost/qr/a84133d3-7855-4cb9-ae2c-f54dee027301", "A84133D3",
                         "F3892ACB"],
                        ["https://billetistan.tibillet.localhost/qr/86dc433c-00ac-479c-93c4-b7a0710246af", "86DC433C",
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
                    CC, created = CarteCashless.objects.get_or_create(
                        number=card[1],
                        tag_id=card[2],
                        uuid_qrcode=uuid_url,
                        origin=origin,
                    )
                    cards_db.append(CC)

                cards_db[0].membre = testMembre
                cards_db[0].save()
                cards_db[1].membre = testMembre
                cards_db[1].save()
                cards_db[2].membre = robocop_membre
                cards_db[2].save()
                cards_db[3].membre = jonas_membre
                cards_db[3].save()
                cards_db[4].membre = framboise_membre
                cards_db[4].save()
                cards_db[22].membre = mike_membre
                cards_db[22].save()

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
                bar2, created = PointDeVente.objects.get_or_create(name="Bar 2", poid_liste=3)
                Boutique, created = PointDeVente.objects.get_or_create(name="Boutique", poid_liste=4)
                PvEspece, created = PointDeVente.objects.get_or_create(
                    name="PvEspece",
                    accepte_especes=True,
                    accepte_carte_bancaire=False,
                    poid_liste=5
                )

                PvCb, created = PointDeVente.objects.get_or_create(
                    name="PvCb",
                    accepte_especes=False,
                    accepte_carte_bancaire=True,
                    poid_liste=6
                )

                carteM, created = CarteMaitresse.objects.get_or_create(carte=cards_db[0], edit_mode=True)
                carteM.points_de_vente.add(Resto)
                carteM.points_de_vente.add(bar1)
                if PointDeVente.objects.filter(name="Badgeuse").exists():
                    carteM.points_de_vente.add(PointDeVente.objects.get(name="Badgeuse"))
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

                carteM6, created = CarteMaitresse.objects.get_or_create(carte=cards_db[22], edit_mode=True)
                carteM6.points_de_vente.add(Resto)
                carteM6.points_de_vente.add(bar1)
                carteM6.points_de_vente.add(Boutique)
                carteM6.points_de_vente.add(PvEspece)
                carteM6.points_de_vente.add(PvCb)
                carteM6.points_de_vente.add(self.pdv_cashless)

                ### FIN DE CREATION DE CARTES

                if os.environ.get('NOM_MONNAIE') == 'Bilstou':
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
                                                                     couleur_backgr=Couleur.objects.get(name='Lime'),
                                                                     icon='fa-wine-bottle',
                                                                     tva=tva20)

                CatMenu, created = Categorie.objects.get_or_create(name="Menu",
                                                                   couleur_backgr=Couleur.objects.get(name='Red'),
                                                                   icon='fa-hamburger',
                                                                   tva=tva85)

                CatDessert, created = Categorie.objects.get_or_create(name="Dessert",
                                                                      couleur_backgr=Couleur.objects.get(name='Orange'),
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
                    Articles.objects.get_or_create(name="Café", prix=1, prix_achat=0.5, methode_choices=Articles.VENTE,
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
                articles.append(Articles.objects.get_or_create(name="Gateau", prix=8, methode_choices=Articles.VENTE,
                                                               methode=vente_article, categorie=CatDessert)[0])

                Resto = PointDeVente.objects.get(name="Resto")
                bar1 = PointDeVente.objects.get(name="Bar 1")
                PvEspece = PointDeVente.objects.get(name="PvEspece")
                PvCb = PointDeVente.objects.get(name="PvCb")

                for art in articles:
                    bar1.articles.add(art) if art not in bar1.articles.all() else art

                for art in articles:
                    Resto.articles.add(art) if art not in Resto.articles.all() else art

                PvEspece.articles.add(articles[1])
                PvCb.articles.add(articles[2])
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

            def config_test(self):
                config = Configuration.get_solo()
                config.structure = os.environ.get('STRUCTURE', "Demo")
                config.siret = "123465789101112"
                config.adresse = "Troisième dune à droite, Tatouine"
                config.pied_ticket = "Nar'trouv vite' !"
                config.telephone = "123456"
                config.email = "contact@tibillet.re"
                config.numero_tva = "456789"

                config.prix_adhesion = os.environ.get('PRIX_ADHESION', 13)

                config.appareillement = True
                config.validation_service_ecran = True
                config.remboursement_auto_annulation = True

                config.billetterie_url = os.environ.get('BILL_TENANT_URL', 'https://demo.tibillet.localhost/')
                # On affiche la string Key sur l'admin de django en message
                # et django.message capitalize chaque message...
                # du coup on fait bien gaffe à ce que je la clée générée ai bien une majusculle au début ...

                api_key = None
                key = " "
                while key[0].isupper() == False:
                    api_key, key = APIKey.objects.create_key(name="billetterie_key")
                    if key[0].isupper() == False:
                        api_key.delete()
                config.key_billetterie = api_key

                # try:
                #     # env.json lisible par la billetterie de test
                #     path = "/populate/env.json"
                #     env_json = json.load(open(path, 'r'))
                #     print(f'{60 * "!"}')
                #     print(f'{key}')
                #     host = os.environ.get('BILL_TENANT_URL').partition('://')[2]
                #     sub_addr = host.partition('.')[0]
                #     env_json['ticketing'][sub_addr]['key_cashless'] = key
                #     with open(path, 'w') as f:
                #         json.dump(env_json, f)
                #     print(f'{60 * "!"}')
                # except Exception as e:
                #     logger.error(f'Impossible de modifier le fichier env.json : {e}')

                ### END TODO

                # Ip du serveur cashless et du ngnix dans le même réseau ( env de test )
                self_ip = socket.gethostbyname(socket.gethostname())
                templist: list = self_ip.split('.')
                templist[-1] = 1
                config.ip_cashless = '.'.join([str(ip) for ip in templist])
                config.billetterie_ip_white_list = '.'.join([str(ip) for ip in templist])

                config.save()

                # env_test = env_json.get('cashlessServer').get(sub)
                # env_root = env_json.get('ticketing').get('root')
                # env_bill = env_json.get('ticketing').get(sub)

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

        if  PointDeVente.objects.count() > 0 :
            logger.error(f'PointDeVente.objects.count() > 0. Pop déja effectué')
        else :
            Lieu(options)
