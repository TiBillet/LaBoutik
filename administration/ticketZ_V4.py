import json
import logging
import statistics
from _decimal import Decimal
from datetime import datetime, timedelta
import dateutil.parser
import numpy as np
import pytz
from django.db.models import Sum, F, Avg
from django.utils.translation import ugettext_lazy as _

from APIcashless.models import Configuration, ArticleVendu, Articles, MoyenPaiement, Assets, Categorie, \
    Membre, ClotureCaisse

logger = logging.getLogger(__name__)


def dround(value):
    return Decimal(value).quantize(Decimal('1.00'))


def ht_from_ttc(ttc, tva):
    return dround(ttc / (1 + (tva / 100)))


def tva_from_ttc(ttc, tva):
    return dround(ttc - ht_from_ttc(ttc, tva))


class TiBilletJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(dround(o))
        elif isinstance(o, datetime):
            return str(o.isoformat())
        elif isinstance(o, np.ndarray):
            return o.tolist()
        return super(TiBilletJsonEncoder, self).default(o)


def start_end_event_4h_am(date, fuseau_horaire=None, heure_pivot=4):
    if fuseau_horaire is None:
        config = Configuration.get_solo()
        fuseau_horaire = config.fuseau_horaire

    tzlocal = pytz.timezone(fuseau_horaire)
    debut_event = tzlocal.localize(datetime.combine(date, datetime.min.time()), is_dst=None) + timedelta(
        hours=heure_pivot)
    fin_event = tzlocal.localize(datetime.combine(date, datetime.min.time()), is_dst=None) + timedelta(
        days=1, hours=heure_pivot)
    return debut_event, fin_event


"""
RECAP DES MOYEN DE PAIEMENTS DIFFERENTS
"""

CREDIT_CARD_NOFED = MoyenPaiement.CREDIT_CARD_NOFED  # 'CC'
CASH = MoyenPaiement.CASH  # 'CA'
CHEQUE = MoyenPaiement.CHEQUE  # 'CH'
STRIPE_NOFED = MoyenPaiement.STRIPE_NOFED
LOCAL_EURO = MoyenPaiement.LOCAL_EURO  # 'LE'
EXTERIEUR_FED = MoyenPaiement.EXTERIEUR_FED  # 'XE'
STRIPE_FED = MoyenPaiement.STRIPE_FED
LOCAL_GIFT = MoyenPaiement.LOCAL_GIFT  # 'LG'
EXTERIEUR_GIFT = MoyenPaiement.EXTERIEUR_FED  # 'XG'
FREE = MoyenPaiement.FREE  # 'NA'
OCECO = MoyenPaiement.OCECO  # 'OC'
FRACTIONNE = MoyenPaiement.FRACTIONNE  # 'FR'
BADGE = MoyenPaiement.BADGE
TIME = MoyenPaiement.TIME
FIDELITY = MoyenPaiement.FIDELITY

# Une liste contient tous les moyens de paiement fiduciaires
CATEGORIES_EURO = [
    CREDIT_CARD_NOFED,  # Carte bancaire
    CASH,  # Espèce
    CHEQUE,  # Chèque
    STRIPE_NOFED,  # Vente en ligne direct (adhésion)
    LOCAL_EURO,  # Cashless local
    EXTERIEUR_FED,  # Cashless local extérieur
    STRIPE_FED,  # Cashless en ligne
]

# Une sous liste qui contient tous les moyens de paiement fiduciaire, mais cashless uniquement
CATEGORIES_CASHLESS = [
    STRIPE_NOFED,  # Vente en ligne direct (adhésion)
    LOCAL_EURO,  # Cashless local
    EXTERIEUR_FED,  # Cashless local extérieur
    STRIPE_FED,  # Cashless en ligne
]

# Une liste qui contient tous les moyens de paiement non fiduciaire, considéré comme offert
CATEGORIES_GIFT = [
    LOCAL_GIFT,  # Cashless cadeau local
    EXTERIEUR_GIFT,  # Cashless fédéré cadeau local
    OCECO,  # Un certain type d'asset extérieur ....
    FREE,
]

# Une liste qui contiens les autres moyens de paiements, non fiduciaires.
CATEGORIES_OTHER = [
    BADGE,
    OCECO,
    TIME,
    FIDELITY,
]


def moyens_de_paiement_euro():
    return MoyenPaiement.objects.filter(categorie__in=CATEGORIES_EURO)


def moyens_de_paiement_cashless():
    return MoyenPaiement.objects.filter(categorie__in=CATEGORIES_CASHLESS)


def moyens_de_paiement_gift():
    return MoyenPaiement.objects.filter(categorie__in=CATEGORIES_GIFT)


def autre_moyen_de_paiement():
    return MoyenPaiement.objects.filter(categorie__in=CATEGORIES_OTHER)


class TicketZ():
    def __init__(self,
                 update_asset=False,
                 rapport=None,
                 calcul_dormante_from_date=False,

                 cloture: ClotureCaisse = None,
                 start_date=None,
                 end_date=None,
                 *args, **kwargs):

        """Ex methode, a virer ?"""
        self.update_asset = update_asset
        self.rapport = rapport
        self.calcul_dormante_from_date = calcul_dormante_from_date
        self.start = datetime.now().timestamp()
        ### Nom des moyens de paiement dans les dictionnaires ###
        self.espece = MoyenPaiement.objects.get(categorie=MoyenPaiement.CASH).get_categorie_display()

        """Methode V4"""
        self.cloture = cloture
        self.config = Configuration.get_solo()
        self.start_date, self.end_date = self.set_start_end_date(start_date, end_date, cloture)
        self.all_articles = self.get_articles()

        logger.info(f"Init ticket Z : {self.start_date} - {self.end_date}")

    ### NEW TABLES V4

    def set_start_end_date(self, start_date, end_date, cloture: ClotureCaisse):
        ### Determine le début et la fin, suivant le rapport généré ou pas.

        # logger.info("calcul valeur")
        if not start_date or end_date:
            if cloture:
                return cloture.start, cloture.end

        try:
            # On vérifie que les start_date et end_date sont bien des objets datetime
            assert isinstance(start_date, datetime)
            assert isinstance(end_date, datetime)
            return start_date, end_date

        except AssertionError:
            # Si ce n'est pas le cas on essaye de les convertir en objet datetime
            start_date = dateutil.parser.parse(start_date)
            end_date = dateutil.parser.parse(end_date)
            return start_date, end_date

        except Exception as e:
            raise AssertionError(
                f"{e} : start_date et end_date doivent être des objets datetime ou formaté en '%Y-%m-%d' ")

    def get_articles(self):
        all_articles = ArticleVendu.objects.filter(
            date_time__gte=self.start_date,
            date_time__lte=self.end_date,
        ).exclude(
            article__methode_choices=Articles.FRACTIONNE,
        ).select_related(
            'article',
            'categorie',
            'responsable',
            'moyen_paiement',
        )
        return all_articles

    def table_vente(self):
        # Une table qui ne comprend que les articles / produits classiques vendus.
        # Ne contient pas les recharges, les adhésions, retour consignes, remboursement
        articles = self.all_articles.filter(
            article__methode_choices__in=[Articles.VENTE, Articles.CASHBACK, Articles.BILLET]
        )

        table = {
            CREDIT_CARD_NOFED:
                articles.filter(moyen_paiement__categorie=CREDIT_CARD_NOFED).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
            CASH: articles.filter(moyen_paiement__categorie=CASH).aggregate(total=Sum(F('qty') * F('prix')))[
                      'total'] or 0,
            CHEQUE: articles.filter(moyen_paiement__categorie=CHEQUE).aggregate(total=Sum(F('qty') * F('prix')))[
                        'total'] or 0,
            STRIPE_NOFED:
                articles.filter(moyen_paiement__categorie=STRIPE_NOFED).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
            LOCAL_EURO:
                articles.filter(moyen_paiement__categorie=LOCAL_EURO).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
            EXTERIEUR_FED:
                articles.filter(moyen_paiement__categorie=EXTERIEUR_FED).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
            STRIPE_FED:
                articles.filter(moyen_paiement__categorie=STRIPE_FED).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
        }
        table['TOTAL'] = sum(table.values())

        # Pour utilisation dans le tableau fond de caisse
        self.sales_cash = table[CASH]
        return table

    def table_recharges(self):
        recharge_locale = self.all_articles.filter(
            article__methode_choices=Articles.RECHARGE_EUROS,
        )

        table = {
            CREDIT_CARD_NOFED:
                recharge_locale.filter(moyen_paiement__categorie=MoyenPaiement.CREDIT_CARD_NOFED).aggregate(
                    total=Sum(F('qty') * F('prix')))['total'] or 0,
            CASH: recharge_locale.filter(moyen_paiement__categorie=MoyenPaiement.CASH).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
            CHEQUE: recharge_locale.filter(moyen_paiement__categorie=MoyenPaiement.CHEQUE).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
        }
        table['TOTAL'] = sum(table.values())

        # Pour utilisation dans le tableau fond de caisse
        self.topin_cash = table[CASH]

        return table

    def table_adhesions(self):
        adhesions = self.all_articles.filter(
            article__methode_choices=Articles.ADHESIONS,
        )

        table = {
            CREDIT_CARD_NOFED: adhesions.filter(moyen_paiement__categorie=MoyenPaiement.CREDIT_CARD_NOFED).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
            CASH: adhesions.filter(moyen_paiement__categorie=MoyenPaiement.CASH).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
            CHEQUE: adhesions.filter(moyen_paiement__categorie=MoyenPaiement.CHEQUE).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
            STRIPE_NOFED: adhesions.filter(moyen_paiement__categorie=MoyenPaiement.STRIPE_NOFED).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
            LOCAL_EURO:
                adhesions.filter(moyen_paiement__categorie=LOCAL_EURO).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
        }
        table['TOTAL'] = sum(table.values())

        # Pour utilisation dans le tableau fond de caisse
        self.membership_cash = table[CASH]

        return table

    def table_retour_consigne(self):
        retour_consigne = self.all_articles.filter(
            article__methode_choices=Articles.RETOUR_CONSIGNE,
        )

        table = {
            CASH: retour_consigne.filter(moyen_paiement__categorie=MoyenPaiement.CASH).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
            LOCAL_EURO: retour_consigne.filter(moyen_paiement__categorie=MoyenPaiement.LOCAL_EURO).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
        }
        table['TOTAL'] = sum(table.values())

        # Pour utilisation dans le tableau fond de caisse
        self.return_consign_cash = table[CASH]
        return table

    def table_remboursement(self):
        remboursement = self.all_articles.filter(
            article__methode_choices__in=[
                Articles.VIDER_CARTE,
                Articles.VOID_CARTE,
            ],
        )

        table = {
            CASH: remboursement.filter(moyen_paiement__categorie=MoyenPaiement.CASH).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
        }
        table['TOTAL'] = sum(table.values())

        # Pour utilisation dans le tableau fond de caisse
        self.refill_cash = table[CASH]
        return table

    def table_tva(self):
        # start = datetime.now().timestamp()
        articles_a_tva = self.all_articles.filter(
            article__methode_choices__in=[Articles.VENTE, Articles.CASHBACK, Articles.BILLET],
            moyen_paiement__categorie__in=CATEGORIES_EURO,
        )

        all_tva = articles_a_tva.order_by('tva').values_list('tva', flat=True).distinct()

        # Création d'un dict avec key : taux, value : ttc
        table_tva = {
            float(tva): {
                "ttc": articles_a_tva.filter(tva=tva).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            } for tva in all_tva}

        # ajout dans le dict le HT et le total TVA
        for tva, val in table_tva.items():
            val['ttc'] = dround(val['ttc'])
            val['ht'] = ht_from_ttc(val['ttc'], Decimal(tva))
            val['tva'] = tva_from_ttc(val['ttc'], Decimal(tva))

        table_tva['TOTAL'] = {
            'ttc': sum(val['ttc'] for val in table_tva.values()),
            'ht': sum(val['ht'] for val in table_tva.values()),
            'tva': sum(val['tva'] for val in table_tva.values()),
        }
        # self.total_collecte_ttc = sum([v['ttc'] for v in dict_TVA_complet.values()])
        # self.total_collecte_ht = sum([v['ht'] for v in dict_TVA_complet.values()])
        # self.total_collecte_tva = sum([v['tva'] for v in dict_TVA_complet.values()])

        return table_tva

    def table_solde_de_caisse(self):
        self.fond_caisse = self.rapport.cash_float if self.rapport else self.config.cash_float

        table = {
            _("Fond de caisse"): self.fond_caisse,
            _("Recharge cashless en espèce"): self.topin_cash,
            _("Remboursement cashless en espèce"): self.refill_cash,
            _("Adhésion en espèce"): self.membership_cash,
            _("Vente directe en espèce"): self.sales_cash,
            _("Retour consigne en espèce"): self.return_consign_cash,
        }
        table['TOTAL'] = sum(table.values())
        return table

    def table_TOTAL_sop(self):  # sop : synthèse des opérations
        # On pourrait faire un bête add sur les valeurs du tableau.
        # Je préfère refaire les calculs depuis la base de donnée pour s'assurer que les valeurs correspondent bien
        all_articles = self.all_articles

        table = {
            CREDIT_CARD_NOFED: all_articles.filter(moyen_paiement__categorie=CREDIT_CARD_NOFED).aggregate(
                total=Sum(F('qty') * F('prix')))['total'] or 0,
            CASH: all_articles.filter(moyen_paiement__categorie=CASH).aggregate(total=Sum(F('qty') * F('prix')))[
                      'total'] or 0,
            CHEQUE: all_articles.filter(moyen_paiement__categorie=CHEQUE).aggregate(total=Sum(F('qty') * F('prix')))[
                        'total'] or 0,
            STRIPE_NOFED:
                all_articles.filter(moyen_paiement__categorie=STRIPE_NOFED).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
            LOCAL_EURO:
                all_articles.filter(moyen_paiement__categorie=LOCAL_EURO).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
            EXTERIEUR_FED:
                all_articles.filter(moyen_paiement__categorie=EXTERIEUR_FED).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
            STRIPE_FED:
                all_articles.filter(moyen_paiement__categorie=STRIPE_FED).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0,
        }
        table['TOTAL'] = sum(table.values())
        return table

    def table_detail_ventes(self):
        articles_vendus = self.all_articles.filter(
            article__methode_choices__in=[Articles.VENTE, Articles.CASHBACK, Articles.BILLET]
        )
        # Fabrication de la ligne catégorie
        table = {categorie: {} for categorie in Categorie.objects.filter(cashless=False).distinct()}

        # Préparation des lignes en fonction de leur prix vendu (un même article peut changer de prix)
        lignes = list(set([(article_v.article, article_v.prix, article_v.prix_achat, article_v.tva) for article_v in
                           articles_vendus]))
        # Pour chaque ligne d'article, on va effectuer les calculs prévu pour les cases
        for ligne in lignes:
            article: Articles = ligne[0]
            prix: Decimal = ligne[1]
            prix_achat: Decimal = ligne[2]
            taux_tva: Decimal = ligne[3]

            categorie: Categorie = article.categorie

            # Tous les articles vendus de ce tuple
            articles_totaux = articles_vendus.filter(article=article, prix=prix, prix_achat=prix_achat)

            vendus = articles_totaux.filter(moyen_paiement__in=moyens_de_paiement_euro())
            offerts = articles_totaux.filter(moyen_paiement__in=moyens_de_paiement_gift())

            total_euro_vendu = vendus.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            cout_total = articles_totaux.aggregate(total=Sum(F('qty') * F('prix_achat')))['total'] or 0
            tva = tva_from_ttc(total_euro_vendu, taux_tva)

            """
            total_ttc_cat += total_euro_vendu
            total_ttc_cat_l.append(total_euro_vendu)
            # total_euro_offert = articles_offerts.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

            """

            # tva = 0
            # if categorie.tva:
            #     tva = tva_from_ttc(total_euro_vendu, categorie.tva.taux)
            # benefice = total_euro_vendu - cout_total - tva

            # Toute les cases du tableau. Le tuple de 3 unique est utilisé comme clé
            table[categorie][ligne] = {
                "name": article.name,
                "qty_vendus": vendus.aggregate(Sum('qty'))['qty__sum'] or 0,
                "qty_offertes": offerts.aggregate(Sum('qty'))['qty__sum'] or 0,
                "qty_totale": articles_totaux.aggregate(Sum('qty'))['qty__sum'] or 0,
                "achat_unit": prix_achat,
                "cout_vendu": vendus.aggregate(total=Sum(F('qty') * F('prix_achat')))['total'] or 0,
                "cout_offert": offerts.aggregate(total=Sum(F('qty') * F('prix_achat')))['total'] or 0,
                "cout_total": cout_total,
                "prix_ttc": prix,
                "taux_tva": taux_tva,
                "prix_tva": tva_from_ttc(prix, taux_tva),
                "prix_ht": prix - tva_from_ttc(prix, taux_tva),
                "chiffre_affaire_ht": tva_from_ttc(total_euro_vendu, taux_tva),
                "chiffre_affaire_ttc": total_euro_vendu,
                "benefice": total_euro_vendu - cout_total - tva,
                # "ca_cadeau_ht": "",
                # "ca_cadeau_ttc": "",
            }

        # Suppression des catégories vides
        table_sans_cat_vide = {k: v for k, v in table.items() if v}
        table = table_sans_cat_vide

        # Calcul du grand TOTAL
        total_global = {
            "name": "TOTAL GLOBAL",
            "qty_vendus": sum(ligne["qty_vendus"] for cat in table.values() for ligne in cat.values()),
            "qty_offertes": sum(ligne["qty_offertes"] for cat in table.values() for ligne in cat.values()),
            "qty_totale": sum(ligne["qty_totale"] for cat in table.values() for ligne in cat.values()),
            "achat_unit": 0,  # Non applicable pour un total
            "cout_vendu": sum(ligne["cout_vendu"] for cat in table.values() for ligne in cat.values()),
            "cout_offert": sum(ligne["cout_offert"] for cat in table.values() for ligne in cat.values()),
            "cout_total": sum(ligne["cout_total"] for cat in table.values() for ligne in cat.values()),
            "prix_ttc": 0,  # Non applicable pour un total
            "taux_tva": 0,  # Non applicable pour un total
            "prix_tva": 0,  # Non applicable pour un total
            "prix_ht": 0,  # Non applicable pour un total
            "chiffre_affaire_ht": sum(ligne["chiffre_affaire_ht"] for cat in table.values() for ligne in cat.values()),
            "chiffre_affaire_ttc": sum(
                ligne["chiffre_affaire_ttc"] for cat in table.values() for ligne in cat.values()),
            "benefice": sum(ligne["benefice"] for cat in table.values() for ligne in cat.values()),
            # "ca_cadeau_ht": sum(ligne["ca_cadeau_ht"] or 0 for ligne in lignes.values()),
            # "ca_cadeau_ttc": sum(ligne["ca_cadeau_ttc"] or 0 for ligne in lignes.values()),
        }

        # Calcul du total dans chaque catégorie :
        for categorie, lignes in table.items():
            table[categorie]['SUBTOTAL'] = {
                "name": "SUBTOTAL",
                "qty_vendus": sum(ligne["qty_vendus"] for ligne in lignes.values()),
                "qty_offertes": sum(ligne["qty_offertes"] for ligne in lignes.values()),
                "qty_totale": sum(ligne["qty_totale"] for ligne in lignes.values()),
                "achat_unit": 0,  # Non applicable pour un total
                "cout_vendu": sum(ligne["cout_vendu"] for ligne in lignes.values()),
                "cout_offert": sum(ligne["cout_offert"] for ligne in lignes.values()),
                "cout_total": sum(ligne["cout_total"] for ligne in lignes.values()),
                "prix_ttc": 0,  # Non applicable pour un total
                "taux_tva": 0,  # Non applicable pour un total
                "prix_tva": 0,  # Non applicable pour un total
                "prix_ht": 0,  # Non applicable pour un total
                "chiffre_affaire_ht": sum(ligne["chiffre_affaire_ht"] for ligne in lignes.values()),
                "chiffre_affaire_ttc": sum(ligne["chiffre_affaire_ttc"] for ligne in lignes.values()),
                "benefice": sum(ligne["benefice"] for ligne in lignes.values()),
                # "ca_cadeau_ht": sum(ligne["ca_cadeau_ht"] or 0 for ligne in lignes.values()),
                # "ca_cadeau_ttc": sum(ligne["ca_cadeau_ttc"] or 0 for ligne in lignes.values()),
            }

        # noinspection PyTypeChecker
        table["TOTAL"] = total_global

        return table

    def table_habitus(self):
        # start = datetime.now().timestamp()
        table_habitus = {
            "cards_count":0,
            "recharge_mediane":0,
            "panier_moyen":0,
            "new_memberships":0,
            "on_card":0,
        }

        articles_vendus_cashless = self.all_articles.filter(carte__isnull=False)
        cards = articles_vendus_cashless.order_by('carte').values_list('carte', flat=True).distinct()

        table_habitus['cards_count'] = cards.count()

        # Tri par carte pour calculer la recharge médiane,
        total_recharge_par_carte = []
        for card in cards:
            # Si la carte a rechargé plusieurs fois, on additionne tout
            toute_recharge_de_la_carte = self.all_articles.filter(
                carte=card,
                article__methode_choices=Articles.RECHARGE_EUROS,
            ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            if toute_recharge_de_la_carte > 0:
                total_recharge_par_carte.append(toute_recharge_de_la_carte)

        # On peut en déduire du coup toute les recharge cashless de la période
        total_recharge_toutes_cartes = sum(total_recharge_par_carte)
        if total_recharge_toutes_cartes >0 :
            table_habitus['recharge_mediane'] = statistics.median(total_recharge_par_carte)

        # Pour calculer le panier moyen, on va chercher toute les dépenses par cartes
        total_depense_par_carte = []
        for card in cards:
            toute_depense_de_la_carte = self.all_articles.filter(
                carte=card,
                moyen_paiement__categorie__in=[LOCAL_EURO, STRIPE_FED, EXTERIEUR_FED],
                article__methode_choices__in=[Articles.VENTE, Articles.CASHBACK, Articles.BILLET],
            ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            # Si la carte a dépensé plus de 0 pendant la période, on prend en compte :
            if toute_depense_de_la_carte > 0:
                total_depense_par_carte.append(toute_depense_de_la_carte)

        # On peut en déduire du coup toute les dépense cashless de la période
        total_depense_toute_carte = sum(total_depense_par_carte)
        if total_depense_toute_carte > 0 :
            table_habitus['panier_moyen'] = statistics.mean(total_depense_par_carte)

        # Nombre d'ahdésions
        table_habitus['new_memberships'] = self.all_articles.filter(
            article__methode_choices=Articles.ADHESIONS).count()

        # Reste sur carte :
        table_habitus['total_on_card'] = total_recharge_toutes_cartes - total_depense_toute_carte
        table_habitus['med_on_card'] = Assets.objects.filter(
            monnaie__categorie__in=[LOCAL_EURO, STRIPE_FED, EXTERIEUR_FED],
            carte__in=cards,
        ).aggregate(Avg('qty'))['qty__avg'] or 0

        return table_habitus


    def context(self):
        return {
            "config": self.config,
            "cloture": self.cloture,
            "start_date": self.start_date,
            "end_date": self.end_date,

            "table_vente": self.table_vente(),
            "table_recharges": self.table_recharges(),
            "table_adhesions": self.table_adhesions(),
            "table_retour_consigne": self.table_retour_consigne(),
            "table_remboursement": self.table_remboursement(),
            "table_solde_de_caisse": self.table_solde_de_caisse(),
            "table_TOTAL_sop": self.table_TOTAL_sop(),
            "table_detail_ventes": self.table_detail_ventes(),
            "table_tva": self.table_tva(),
            "table_habitus": self.table_habitus(),
            "comments": self.all_articles.filter(comment__isnull=False).values_list('comment', flat=True),

            "fond_caisse": self.fond_caisse,
            "categories": dict(MoyenPaiement.CATEGORIES),
            "responsables": self.all_articles.values('responsable__id', 'responsable__name').order_by().distinct(
                'responsable'),
            "pos": self.all_articles.values('pos__id', 'pos__name').order_by().distinct('pos'),
        }


    ### EX TABLE

    def _classement_lignes_tableau_vente(self) -> ArticleVendu.objects:
        """
        @param date:
        @return: ArticleVendu
        @type config: Configuration
        """
        # logger.info("TICKETZ : on va chercher et classer les articles vendus")

        # Tous les articles vendus
        self.lignes_tableau_vente = ArticleVendu.objects.filter(
            date_time__gte=self.start_date,
            date_time__lte=self.end_date,
        ).exclude(
            article__methode_choices__in=[Articles.FRACTIONNE, Articles.BADGEUSE],
        )

        # if not self.lignes_tableau_vente:
        #     logger.warning(Exception("Aucune ventes à cette date"))
        #     return False

        self.articles_vendus = self.lignes_tableau_vente.filter(
            article__methode_choices__in=[Articles.VENTE, Articles.CASHBACK, Articles.BILLET]
        )

        self.articles_vendus_euro = self.articles_vendus.filter(
            moyen_paiement__in=moyens_de_paiement_euro()
        )

        self.articles_vendus_gift = self.articles_vendus.filter(
            moyen_paiement__in=moyens_de_paiement_gift()
        )

        logger.info(f"Temps de calcul de _classement_lignes_tableau_vente : {datetime.now().timestamp() - self.start}")

        return self.articles_vendus


    def _quantite_vendus(self):
        """
        Renvoie un tuple contenant :
        - un dictionnaire avec les quantités vendues classé par catégories
        - Le total recette en euro
        @rtype: object
        """
        start = datetime.now().timestamp()
        articles_vendus = self.articles_vendus
        list_uuid = set(articles_vendus.values_list('categorie', flat=True).distinct())
        dict_quantites_vendus = {
            Categorie.objects.get(pk=cat): dict()
            for cat in list_uuid if cat
        }

        total_ttc_cat = 0
        total_ttc_cat_l = []
        for categorie in dict_quantites_vendus:
            categorie: Categorie

            article_vendu_categorie = self.articles_vendus.filter(categorie=categorie)

            # Dans le cas ou le prix change en cours de journée,
            # on classe par tuple (article_vendu, prix, prix_achat)
            # Si le prix change suivant la journée ou le mois, nous aurons une seconde ligne
            lignes = list(set([(article_v.article, article_v.prix, article_v.prix_achat) for article_v in
                               article_vendu_categorie]))

            for ligne in lignes:
                article: Articles = ligne[0]
                prix: Decimal = ligne[1]
                prix_achat: Decimal = ligne[2]

                # Tous les articles vendus de ce tuple
                articles_totaux = article_vendu_categorie.filter(article=article, prix=prix, prix_achat=prix_achat)

                vendus = articles_totaux.filter(moyen_paiement__in=moyens_de_paiement_euro())
                offerts = articles_totaux.filter(moyen_paiement__in=moyens_de_paiement_gift())

                qty_vendus = vendus.aggregate(Sum('qty'))['qty__sum'] or 0
                qty_offertes = offerts.aggregate(Sum('qty'))['qty__sum'] or 0
                qty_totale = articles_totaux.aggregate(Sum('qty'))['qty__sum'] or 0

                cout_vendu = vendus.aggregate(total=Sum(F('qty') * F('prix_achat')))['total'] or 0
                cout_offert = offerts.aggregate(total=Sum(F('qty') * F('prix_achat')))['total'] or 0
                cout_total = articles_totaux.aggregate(total=Sum(F('qty') * F('prix_achat')))['total'] or 0

                total_euro_vendu = vendus.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
                total_ttc_cat += total_euro_vendu
                total_ttc_cat_l.append(total_euro_vendu)
                # total_euro_offert = articles_offerts.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

                tva = 0
                if categorie.tva:
                    tva = tva_from_ttc(total_euro_vendu, categorie.tva.taux)
                benefice = total_euro_vendu - cout_total - tva

                nom_ligne = f"{article} ({prix}/{prix_achat})"
                dict_quantites_vendus[categorie][nom_ligne] = [
                    qty_vendus,
                    qty_offertes,
                    qty_totale,
                    cout_vendu,
                    cout_offert,
                    cout_total,
                    tva,
                    benefice,
                    total_euro_vendu,
                ]

            ## Calcul du total de la catégorie
            vendus_cat = article_vendu_categorie.filter(moyen_paiement__in=moyens_de_paiement_euro())
            offerts_cat = article_vendu_categorie.filter(moyen_paiement__in=moyens_de_paiement_gift())
            total_euro_vendu_cat = vendus_cat.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            cout_total_cat = article_vendu_categorie.aggregate(total=Sum(F('qty') * F('prix_achat')))['total'] or 0

            tva = 0
            if categorie.tva:
                tva = tva_from_ttc(total_euro_vendu_cat, categorie.tva.taux)

            benefice = total_euro_vendu_cat - cout_total_cat - tva

            dict_quantites_vendus[categorie]['total'] = [
                # qty_vendus,
                vendus_cat.aggregate(Sum('qty'))['qty__sum'] or 0,
                # qty_offertes,
                offerts_cat.aggregate(Sum('qty'))['qty__sum'] or 0,
                # qty_totale,
                article_vendu_categorie.aggregate(Sum('qty'))['qty__sum'] or 0,
                # cout_vendu,
                vendus_cat.aggregate(total=Sum(F('qty') * F('prix_achat')))['total'] or 0,
                # cout_offert,
                offerts_cat.aggregate(total=Sum(F('qty') * F('prix_achat')))['total'] or 0,
                # cout_total,
                cout_total_cat,
                # tva,
                tva,
                # benefice,
                benefice,
                # total_euro_vendu,
                total_euro_vendu_cat
            ]

        # Calcul du big total
        list_total = [cat['total'] for cat in dict_quantites_vendus.values()]
        dict_quantites_vendus['total'] = [sum(elements) for elements in zip(*list_total)]
        try:
            self.total_TTC = dict_quantites_vendus['total'][8]
        except IndexError as e:
            logger.warning(f"Pas d'article vendu, total = 0")
            self.total_TTC = 0

        logger.info(f"Temps de calcul de _quantite_vendus : {datetime.now().timestamp() - start}")

        # self.total_TTC = big_total[8]
        self.dict_quantites_vendus = dict_quantites_vendus

        return dict_quantites_vendus


    def _tva(self):
        # start = datetime.now().timestamp()

        # Tableau TVA
        articles_vendus_euro = self.articles_vendus_euro
        if articles_vendus_euro == None:
            raise Exception("Valeur non calculée, lancez calcul_valeurs()")

        all_tva = set(articles_vendus_euro.values_list('tva', flat=True).distinct())

        ### EX TABLEAU TV, a retirer ?
        dict_TVA = {
            tva:
                tva_from_ttc(articles_vendus_euro.filter(tva=tva).aggregate(total=Sum(F('qty') * F('prix')))[
                                 'total'], tva) or 0
            for tva in all_tva if tva
        }
        self.total_collecte_toute_tva = sum([v for v in dict_TVA.values()])
        self.dict_TVA = dict_TVA

        dict_TVA_complet = {
            float(tva): {
                "ttc": articles_vendus_euro.filter(tva=tva).aggregate(total=Sum(F('qty') * F('prix')))[
                           'total'] or 0
            }
            for tva in all_tva
        }

        for tva, val in dict_TVA_complet.items():
            val['ttc'] = dround(val['ttc'])
            val['ht'] = ht_from_ttc(val['ttc'], Decimal(tva))
            val['tva'] = tva_from_ttc(val['ttc'], Decimal(tva))

        self.dict_TVA_complet = dict_TVA_complet

        self.total_collecte_ttc = sum([v['ttc'] for v in dict_TVA_complet.values()])
        self.total_collecte_ht = sum([v['ht'] for v in dict_TVA_complet.values()])
        self.total_collecte_tva = sum([v['tva'] for v in dict_TVA_complet.values()])

        # logger.info(f"Temps de calcul de _tva : {datetime.now().timestamp() - start}")
        return self.total_collecte_toute_tva


    def _recharge_locale(self):
        # start = datetime.now().timestamp()
        # Tableau du récap de recharge cashless
        recharge_locale = self.lignes_tableau_vente.filter(
            article__methode_choices=Articles.RECHARGE_EUROS,
        )

        recharge_locale_cadeau = self.lignes_tableau_vente.filter(
            article__methode_choices=Articles.RECHARGE_CADEAU
        )

        list_mp_recharge_locale = set(recharge_locale.values_list('moyen_paiement', flat=True).distinct())
        dict_moyenPaiement_recharge = {
            MoyenPaiement.objects.get(pk=mp).get_categorie_display():
                recharge_locale.filter(moyen_paiement=mp).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            for mp in list_mp_recharge_locale if mp
        }

        total_recharge = recharge_locale.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
        total_recharge_cadeau = recharge_locale_cadeau.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

        self.dict_moyenPaiement_recharge = dict_moyenPaiement_recharge
        self.recharge_cash = self.dict_moyenPaiement_recharge.get(self.espece, 0)
        self.total_recharge = total_recharge
        self.total_recharge_cadeau = total_recharge_cadeau
        self.recharge_locale = recharge_locale

        # logger.info(f"Temps de calcul de _recharge_locale : {datetime.now().timestamp() - start}")

        return total_recharge


    def _retour_consigne(self):
        retour_consignes_espece = self.lignes_tableau_vente.filter(
            article__methode_choices=Articles.RETOUR_CONSIGNE,
            moyen_paiement__categorie=MoyenPaiement.CASH
        ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
        self.retour_consignes_espece = dround(retour_consignes_espece)

        retour_consignes_cashless = self.lignes_tableau_vente.filter(
            article__methode_choices=Articles.RETOUR_CONSIGNE,
            moyen_paiement__categorie=MoyenPaiement.LOCAL_EURO
        ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
        # En absolu pour que ça soit compté comme des recharges
        self.retour_consignes_cashless = dround(abs(retour_consignes_cashless))

        retour_consignes_cb = self.lignes_tableau_vente.filter(
            article__methode_choices=Articles.RETOUR_CONSIGNE,
            moyen_paiement__categorie=MoyenPaiement.CREDIT_CARD_NOFED
        ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
        self.retour_consignes_cb = dround(retour_consignes_cb)

        self.retour_consigne_total = (abs(retour_consignes_espece) +
                                      abs(retour_consignes_cashless) +
                                      abs(retour_consignes_cb))


    def _remboursement_local(self):
        # Les vider et void carte :
        remboursement_local = self.lignes_tableau_vente.filter(
            article__methode_choices__in=[
                Articles.VIDER_CARTE,
                Articles.VOID_CARTE,
            ],
        )

        list_mp_remboursement_local = set(remboursement_local.values_list('moyen_paiement', flat=True).distinct())
        dict_moyenPaiement_remboursement = {
            MoyenPaiement.objects.get(pk=mp).get_categorie_display():
                remboursement_local.filter(moyen_paiement=mp).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            for mp in list_mp_remboursement_local if mp
        }

        self.dict_moyenPaiement_remboursement = dict_moyenPaiement_remboursement
        self.remboursement_espece = dict_moyenPaiement_remboursement.get(self.espece, 0)

        self.total_remboursement = remboursement_local.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
        self.total_cashless = self.total_recharge - abs(self.total_remboursement) + abs(self.retour_consignes_cashless)

        # logger.info(f"Temps de calcul de _remboursement_local : {datetime.now().timestamp() - start}")
        return self.total_remboursement


    def _vente_par_moyen_de_paiement(self):
        # start = datetime.now().timestamp()

        articles_vendus_euros = self.articles_vendus_euro
        articles_vendus_gift = self.articles_vendus_gift

        list_mp_articles_vendus_euros = set(articles_vendus_euros.values_list('moyen_paiement', flat=True).distinct())
        list_mp_articles_vendus_gift = set(articles_vendus_gift.values_list('moyen_paiement', flat=True).distinct())

        # Tableau de tous les moyens de paiements considéré comme EURO
        self.dict_moyenPaiement_euros = {
            MoyenPaiement.objects.get(pk=mp).get_categorie_display():
                articles_vendus_euros.filter(moyen_paiement=mp).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            for mp in list_mp_articles_vendus_euros if mp
        }

        self.dict_moyenPaiement_gift = {
            MoyenPaiement.objects.get(pk=mp).get_categorie_display():
                articles_vendus_gift.filter(moyen_paiement=mp).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            for mp in list_mp_articles_vendus_gift if mp
        }

        self.ventes_directe_espece = self.dict_moyenPaiement_euros.get(self.espece, 0)

        self.total_euro_by_mp = articles_vendus_euros.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
        self.total_gift_by_mp = articles_vendus_gift.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

        # logger.info(f"Temps de calcul de _classement_par_moyen_paiement : {datetime.now().timestamp() - start}")

        return self.dict_moyenPaiement_euros


    def _monnaie_dormante(self):
        # start = datetime.now().timestamp()

        self.dormante_euro = \
            Assets.objects.filter(monnaie__categorie=MoyenPaiement.LOCAL_EURO).aggregate(Sum('qty'))['qty__sum']

        self.reste_moyenne = dround(
            Assets.objects.filter(monnaie__categorie=MoyenPaiement.LOCAL_EURO).aggregate(Avg('qty'))['qty__avg'] or 0
        )

        self.dormante_gift = \
            Assets.objects.filter(monnaie__categorie=MoyenPaiement.LOCAL_GIFT).aggregate(Sum('qty'))['qty__sum']

        if self.calcul_dormante_from_date:
            recharge_local_from_beggining = ArticleVendu.objects.filter(
                article__methode_choices=Articles.RECHARGE_EUROS,
                date_time__lte=self.end_date,
            ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

            recharge_cadeau_from_beggining = ArticleVendu.objects.filter(
                article__methode_choices=Articles.RECHARGE_CADEAU,
                date_time__lte=self.end_date,
            ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

            remboursement_local_from_beggining = ArticleVendu.objects.filter(
                article__methode_choices__in=[
                    Articles.VIDER_CARTE,
                    Articles.VOID_CARTE,
                ],
                date_time__lte=self.end_date,
            ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

            vente_cashless_from_begginin = ArticleVendu.objects.filter(
                article__methode_choices=Articles.VENTE,
                moyen_paiement__categorie=MoyenPaiement.LOCAL_EURO,
                date_time__lte=self.end_date,
            ).exclude(
                article__methode_choices=Articles.FRACTIONNE
            ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

            vente_cadeau_from_begginin = ArticleVendu.objects.filter(
                article__methode_choices=Articles.VENTE,
                moyen_paiement__categorie=MoyenPaiement.LOCAL_GIFT,
                date_time__lte=self.end_date,
            ).exclude(
                article__methode_choices=Articles.FRACTIONNE
            ).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

            self.dormante_euro = recharge_local_from_beggining - vente_cashless_from_begginin - abs(
                remboursement_local_from_beggining)
            self.dormante_gift = recharge_cadeau_from_beggining - vente_cadeau_from_begginin

            # logger.info(f"Temps de calcul de _monnaie_dormante : {datetime.now().timestamp() - start}")

        if self.rapport:
            # Si le rapport est tout neuf, (==0)
            # ou si on demande un update volontairement (dans le post_save ArticleVendu)
            # Calcul de la monnaie restante :
            if self.rapport.monnaie_restante == 0 or self.update_asset:
                self.rapport.monnaie_restante = self.dormante_euro
                self.rapport.cadeau_restant = self.dormante_gift

        return True


    def _delta(self):
        # start = datetime.now().timestamp()

        if self.dict_moyenPaiement_euros == None or self.dict_moyenPaiement_gift == None:
            raise Exception("Valeur non calculée, lancez calcul_valeurs()")

        total_vente_local_euro = self.dict_moyenPaiement_euros.get(
            MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO).name, 0)
        total_vente_local_gift = self.dict_moyenPaiement_gift.get(
            MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT).name, 0)

        delta_cashless_euro = self.total_cashless - total_vente_local_euro
        delta_cashless_gift = self.total_recharge_cadeau - total_vente_local_gift

        # import ipdb; ipdb.set_trace()
        self.delta_cashless_euro = delta_cashless_euro
        self.delta_cashless_gift = delta_cashless_gift

        if self.rapport:
            self.rapport.delta_monnaie = delta_cashless_euro
            self.rapport.delta_cadeau = delta_cashless_gift

        # logger.info(f"Temps de calcul de _delta : {datetime.now().timestamp() - start}")
        return True


    def _adhesion(self):
        # start = datetime.now().timestamp()

        adhesions = self.lignes_tableau_vente.filter(article__methode_choices=Articles.ADHESIONS)
        self.total_adhesion = adhesions.count()
        self.total_adhesion_euro = adhesions.aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0

        # Utilisation de l'ORM de Django pour calculer le produit (tarif * quantité) pour chaque vente directeement en SQL.
        totals = adhesions.annotate(product=F('prix') * F('qty')).values_list('product', flat=True)

        # Construction du tableau numpy pour calculer les valeurs uniques et les occurrences.
        tableau_decimals = np.array(totals)
        # Obtenir les valeurs uniques et leurs occurrences
        valeurs_uniques, occurrences = np.unique(tableau_decimals, return_counts=True)
        dict_adhesions = {f"{dround(value)}": int(count) for value, count in zip(valeurs_uniques, occurrences)}

        adhesions_mp = set(adhesions.values_list('moyen_paiement', flat=True).distinct())

        dict_adhesion_par_moyen_paiement = {
            MoyenPaiement.objects.get(pk=mp).get_categorie_display():
                adhesions.filter(moyen_paiement=mp).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0
            for mp in adhesions_mp if mp
        }

        self.dict_adhesion_par_moyen_paiement = dict_adhesion_par_moyen_paiement
        self.adhesion_espece = dict_adhesion_par_moyen_paiement.get(self.espece, 0)
        self.dict_adhesions = dict_adhesions
        # logger.info(f"Temps de calcul de _adhesion : {datetime.now().timestamp() - start}")

        return dict_adhesions


    def _fond_caisse(self):
        # start = datetime.now().timestamp()

        if self.rapport:
            self.fond_caisse = self.rapport.cash_float if self.rapport.cash_float else self.config.cash_float
        else:
            self.fond_caisse = self.config.cash_float

        self.total_cash = dround(
            self.recharge_cash +
            self.ventes_directe_espece +
            self.fond_caisse +
            self.adhesion_espece +
            self.remboursement_espece +
            self.retour_consignes_espece
        )

        # logger.info(f"Temps de calcul de _fond_caisse : {datetime.now().timestamp() - start}")
        return self.fond_caisse


    def _recap_toutes_entrees(self):
        start = datetime.now().timestamp()
        list_uuid = set(self.lignes_tableau_vente.values_list('moyen_paiement', flat=True).distinct())

        toutes_ventes = self.lignes_tableau_vente.exclude(
            moyen_paiement__categorie=MoyenPaiement.BADGE
        )

        dict_toute_entrees_par_moyen_paiement = {
            MoyenPaiement.objects.get(pk=mp).get_categorie_display():
                toutes_ventes.filter(moyen_paiement=mp).aggregate(total=Sum(F('qty') * F('prix')))[
                    'total'] or 0
            for mp in list_uuid if mp
        }

        # logger.info(f"Temps de calcul de _recap_toutes_entrees : {datetime.now().timestamp() - start}")
        # import ipdb; ipdb.set_trace()
        self.dict_toute_entrees_par_moyen_paiement = dict_toute_entrees_par_moyen_paiement


    def _badgeuse(self):
        articles_badge = ArticleVendu.objects.filter(article__methode_choices=Articles.BADGEUSE)
        if articles_badge.exists() > 0:
            self.cartes_badgees_qty = len(set(articles_badge.values_list('carte', flat=True).distinct()))
        else:
            self.cartes_badgees_qty = None


    def _habitus(self):
        # start = datetime.now().timestamp()

        articles_vendus_cashless = self.articles_vendus.filter(carte__isnull=False)
        carte_distinct = set(articles_vendus_cashless.values_list('carte', flat=True).distinct())
        self.nbr_carte_distinct = len(carte_distinct)

        # Tri par carte. 0 = total recharge, 1 = total depense
        recharge_par_carte = {
            carte_uuid: [
                self.recharge_locale.filter(carte=carte_uuid).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0,
                self.articles_vendus.filter(carte=carte_uuid).aggregate(total=Sum(F('qty') * F('prix')))['total'] or 0,
            ]
            for carte_uuid in carte_distinct if carte_uuid
        }

        all_recharge = [recharge[0] for recharge in recharge_par_carte.values() if recharge[0] > 0]

        self.recharge_mediane = 0
        if all_recharge:
            self.recharge_mediane = statistics.median(all_recharge)

        self.depense_mediane, self.panier_moyen = 0, 0
        all_depense = [depense[1] for depense in recharge_par_carte.values() if depense[1] > 0]
        if all_depense:
            self.depense_mediane = statistics.median(all_depense)
            self.panier_moyen = statistics.mean(all_depense)

        nouveaux_membres = Membre.objects.filter(date_ajout__gte=self.start_date, date_ajout__lte=self.end_date).count()
        self.nouveaux_membres = nouveaux_membres

        # logger.info(f"Temps de calcul de _habitus : {datetime.now().timestamp() - start}")


    def _to_dict(self):
        context = {
            'start_date': self.start_date,
            'end_date': self.end_date,

            'structure': self.config.structure,

            'dict_quantites_vendus': self.dict_quantites_vendus,
            'total_TTC': self.total_TTC,

            'dict_TVA': self.dict_TVA,
            'total_collecte_toute_tva': self.total_collecte_toute_tva,

            'dict_TVA_complet': self.dict_TVA_complet,
            'total_collecte_ttc': self.total_collecte_ttc,
            'total_collecte_ht': self.total_collecte_ht,
            'total_collecte_tva': self.total_collecte_tva,

            'total_HT': (self.total_TTC - self.total_collecte_toute_tva),

            'dict_moyenPaiement_euros': self.dict_moyenPaiement_euros,
            'total_euro_by_mp': self.total_euro_by_mp,

            'dict_moyenPaiement_gift': self.dict_moyenPaiement_gift,
            'total_gift_by_mp': self.total_gift_by_mp,

            'nom_monnaie': MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO).name,
            'nom_monnaie_cadeau': MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT).name,

            'dict_moyenPaiement_recharge': self.dict_moyenPaiement_recharge,
            "dict_moyenPaiement_remboursement": self.dict_moyenPaiement_remboursement,
            'total_recharge': self.total_recharge,
            'total_recharge_cadeau': self.total_recharge_cadeau,

            'retour_consignes_espece': self.retour_consignes_espece,
            'retour_consignes_cashless': self.retour_consignes_cashless,
            'retour_consignes_cb': self.retour_consignes_cb,
            'retour_consigne_total': self.retour_consigne_total,

            "total_remboursement": self.total_remboursement,
            "remboursement_espece": self.remboursement_espece,
            "total_cashless": self.total_cashless,

            "fond_caisse": self.fond_caisse,

            "recharge_cash": self.recharge_cash,
            "ventes_directe_espece": self.ventes_directe_espece,
            "total_cash": self.total_cash,

            "cartes_badgees_qty": self.cartes_badgees_qty,
            "nbr_carte_distinct": self.nbr_carte_distinct,
            "recharge_mediane": self.recharge_mediane,
            "depense_mediane": self.depense_mediane,
            "panier_moyen": self.panier_moyen,
            "reste_moyenne": self.reste_moyenne,
            "nouveaux_membres": self.nouveaux_membres,

            "dormante_j_rapport": self.dormante_euro,
            "dormante_gift_j_rapport": self.dormante_gift,
            "delta_cashless_euro": self.delta_cashless_euro,
            "delta_cashless_gift": self.delta_cashless_gift,

            "dict_adhesions": self.dict_adhesions,
            "total_adhesion": self.total_adhesion,
            "total_adhesion_euro": self.total_adhesion_euro,
            "dict_adhesion_par_moyen_paiement": self.dict_adhesion_par_moyen_paiement,
            "adhesion_espece": self.adhesion_espece,

            'dict_toute_entrees_par_moyen_paiement': self.dict_toute_entrees_par_moyen_paiement,
        }

        self.to_dict = context
        return context


    def _to_json(self):
        # Transformation des object ORM en string pour SERIALIZER
        # noinspection PyUnresolvedReferences
        context_to_json = self.to_dict.copy()
        dict_quantites_vendus_to_json = self.dict_quantites_vendus.copy()

        # Conversion des objects ORM categories en string :
        context_to_json['dict_quantites_vendus'] = {f"{k}": v for k, v in dict_quantites_vendus_to_json.items()}

        context_to_json['dict_TVA'] = {str(k): v for k, v in self.dict_TVA.items()}

        # context_to_json['dict_moyenPaiement_recharge'] = {k.name: v for k, v in
        #                                                   self.dict_moyenPaiement_recharge.items() if k}

        # context_to_json["dict_moyenPaiement_remboursement"] = {k.name: v for k, v in
        #                                                        self.dict_moyenPaiement_remboursement.items() if k}

        # articles_sans_cout = self.articles_sans_cout
        # context_to_json['articles_sans_cout'] = [art.name for art in self.articles_sans_cout]

        context_json = json.dumps(context_to_json, cls=TiBilletJsonEncoder)
        self.to_json = context_json

        return context_json


    def calcul_valeurs(self):
        # logger.info("calcul valeur")
        if not self.start_date or self.end_date:
            if self.rapport:
                date = self.rapport.date
                self.start_date, self.end_date = start_end_event_4h_am(date, fuseau_horaire=self.config.fuseau_horaire)

        # On vérifie que les start_date et end_date sont bien des objets datetime
        try:
            # logger.info(
            #     f"Type start_date ({type(self.start_date)}) et type end_date ({type(self.end_date)})")
            assert isinstance(self.start_date, datetime)
            assert isinstance(self.end_date, datetime)
        except AssertionError:
            # Si ce n'est pas le cas on essaye de les convertir en objet datetime
            # logger.info(
            #     f"start_date ({self.start_date}) et end_date ({self.end_date}) doivent être des objets datetime, on test avec strptime")
            import dateutil.parser
            # noinspection PyTypeChecker
            self.start_date = dateutil.parser.parse(self.start_date)
            # noinspection PyTypeChecker
            self.end_date = dateutil.parser.parse(self.end_date)

        except Exception as e:
            raise AssertionError(
                f"{e} : start_date et end_date doivent être des objets datetime ou formaté en '%Y-%m-%d' ")

        # On calcule toutes les valeurs nécéssaires au tableau
        if not ArticleVendu.objects.filter(
                date_time__gte=self.start_date,
                date_time__lte=self.end_date,
        ):
            logger.warning(Exception("Aucune ventes à cette date"))
            return False

        self.articles_vendus = self._classement_lignes_tableau_vente()
        self.quantite_vendus = self._quantite_vendus()
        self.total_collecte_toute_tva = self._tva()
        self._retour_consigne()
        self.total_recharge = self._recharge_locale()
        self.total_remboursement = self._remboursement_local()
        self.dict_moyenPaiement_euros = self._vente_par_moyen_de_paiement()

        self._monnaie_dormante()
        self._delta()
        self._adhesion()
        self._fond_caisse()
        self._habitus()
        self._badgeuse()
        self._recap_toutes_entrees()
        self._to_dict()
        self._to_json()

        if self.rapport:
            self.rapport.chiffre_affaire = self.total_TTC
            self.rapport.save()

        # import ipdb; ipdb.set_trace()
        # logger.info(f"Calcul cloture du {self.start_date} au {self.end_date} - lignes_tableau_vente.count : {self.lignes_tableau_vente.count()}")
        logger.info(f"Temps de calcul de calcul_valeurs : {datetime.now().timestamp() - self.start}")
        return True
