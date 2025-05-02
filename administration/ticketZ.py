import json
import logging
import statistics
from _decimal import Decimal
from datetime import datetime, timedelta

import numpy as np
import pytz
from django.db.models import Sum, F, Avg

from APIcashless.models import Configuration, ArticleVendu, Articles, MoyenPaiement, Assets, Categorie, \
    Membre

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


def moyens_de_paiement_euro():
    categories_euros = [
        MoyenPaiement.LOCAL_EURO,
        MoyenPaiement.STRIPE_FED,
        MoyenPaiement.STRIPE_NOFED,
        MoyenPaiement.CASH,
        MoyenPaiement.CREDIT_CARD_NOFED,
        MoyenPaiement.CHEQUE,
        MoyenPaiement.EXTERIEUR_FED
    ]
    return MoyenPaiement.objects.filter(categorie__in=categories_euros)


def moyens_de_paiement_cashless():
    categories_euros = [
        MoyenPaiement.LOCAL_EURO,
        MoyenPaiement.STRIPE_FED,
        MoyenPaiement.STRIPE_NOFED,
    ]
    return MoyenPaiement.objects.filter(categorie__in=categories_euros)


def moyens_de_paiement_gift():
    categories_euros = [
        MoyenPaiement.LOCAL_GIFT,
        MoyenPaiement.EXTERIEUR_GIFT,
        MoyenPaiement.OCECO,
    ]
    return MoyenPaiement.objects.filter(categorie__in=categories_euros)


def autre_moyen_de_paiement():
    categories = [
        MoyenPaiement.BADGE,
        MoyenPaiement.OCECO,
        MoyenPaiement.TIME,
        MoyenPaiement.FIDELITY,
    ]
    return MoyenPaiement.objects.filter(categorie__in=categories)


class TicketZ():
    def __init__(self,
                 rapport=None,
                 update_asset=False,
                 start_date=None,
                 end_date=None,
                 calcul_dormante_from_date=False,
                 *args, **kwargs):

        self.update_asset = update_asset
        self.config = Configuration.get_solo()
        self.rapport = rapport
        self.start_date = start_date
        self.end_date = end_date
        self.calcul_dormante_from_date = calcul_dormante_from_date
        self.start = datetime.now().timestamp()

        ### Nom des moyens de paiement dans les dictionnaires ###
        self.espece = MoyenPaiement.objects.get(categorie=MoyenPaiement.CASH).get_categorie_display()
        logger.info(f"Init ticket Z : {self.start_date} - {self.end_date}")

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
            article__methode_choices__in=[Articles.VENTE, Articles.CASHBACK]
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
