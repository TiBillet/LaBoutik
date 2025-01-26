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
    ClotureCaisse

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

        # noinspection PyTypeChecker
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

            vendus = articles_totaux.filter(moyen_paiement__categorie__in=CATEGORIES_EURO)
            offerts = articles_totaux.filter(moyen_paiement__categorie__in=CATEGORIES_GIFT)

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
            "cards_count": 0,
            "recharge_mediane": 0,
            "panier_moyen": 0,
            "new_memberships": 0,
            "on_card": 0,
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
        if total_recharge_toutes_cartes > 0:
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
        if total_depense_toute_carte > 0:
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
