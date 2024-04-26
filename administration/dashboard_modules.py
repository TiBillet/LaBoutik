from jet.dashboard.modules import DashboardModule
from APIcashless.models import *
from django.utils.translation import ugettext_lazy as _
from datetime import datetime as dt
from datetime import timedelta
from django.db.models import Sum

from administration.ticketZ import TicketZ


class chartMonnaie(DashboardModule):
    title = _('chartMonnaie')
    template = 'dashboard/chartMonnaie.html'

    def __init__(self, title=None, limit=10, **kwargs):
        kwargs.update({'limit': limit})
        super(chartMonnaie, self).__init__(title, **kwargs)

    def init_with_context(self, context):

        jours = []
        liste_chiffre_affaire_vente = []

        rapports = ClotureCaisse.objects.filter(
            start__gte=timezone.now() - timedelta(days=60),
            categorie=ClotureCaisse.CLOTURE,
        ).order_by('start')

        for rapport in rapports:
            ca = dround(rapport.chiffre_affaire())
            if ca > 1:
                jours.append(rapport.start.strftime("%m-%d"))
                liste_chiffre_affaire_vente.append(ca)

        self.children = {
            'labels': jours,
            'liste_chiffre_affaire_vente': liste_chiffre_affaire_vente,
        }


class TempsReel(DashboardModule):
    title = _('Temps réel')
    template = 'dashboard/TempsReel.html'

    def init_with_context(self, context):
        config = Configuration.get_solo()
        heure_cloture = config.cloture_de_caisse_auto
        matin = timezone.make_aware(dt.combine(timezone.localdate(), heure_cloture))
        ticketZ = TicketZ(start_date=matin, end_date=timezone.localtime())
        if ticketZ.calcul_valeurs():
            dict_toute_entrees_par_moyen_paiement = ticketZ.dict_toute_entrees_par_moyen_paiement

            try:
                children = [{
                        'title': f"{name}",
                        'value': f"{dround(value)} €",
                    } for name, value in dict_toute_entrees_par_moyen_paiement.items() ]
                children.append(
                    {
                        'title': _('C.A. TTC'),
                        'value': f"{dround(ticketZ.total_TTC)} €",
                    },
                )

                # Création du tupple avec la virgule
                self.children = children,

            except Exception as e:
                logger.warning(f"DASHBOARD : Erreur lors du calcul de la monnaie disponible. Db toute neuve ? : {e}")


class Informations(DashboardModule):
    title = _('Monnaie Disponible')
    template = 'dashboard/informations.html'

    def __init__(self, title=None, limit=10, **kwargs):
        kwargs.update({'limit': limit})
        super(Informations, self).__init__(title, **kwargs)

    def init_with_context(self, context):
        # self.children = qs.select_related('content_type', 'user')[:int(self.limit)]
        configuration = Configuration.get_solo()

        try:
            total_monnaie = Assets.objects.filter(monnaie__categorie=MoyenPaiement.LOCAL_EURO).aggregate(Sum('qty'))[
                'qty__sum']
            total_monnaie_cadeau = \
                Assets.objects.filter(monnaie__categorie=MoyenPaiement.LOCAL_GIFT).aggregate(Sum('qty'))['qty__sum']

            self.children = [
                {
                    'title': _('Membres'),
                    'value': Membre.objects.count(),
                },
                {
                    'title': _('Cartes'),
                    'value': CarteCashless.objects.filter(assets__isnull=False).distinct().count(),
                },
                {
                    'title': f"{configuration.monnaie_principale}",
                    'value': format(round(total_monnaie, 2), '.2f')
                },
                {
                    'title': f"{configuration.monnaie_principale_cadeau}",
                    'value': format(round(total_monnaie_cadeau, 2), '.2f'),
                },
            ],

        except Exception as e:
            logger.warning(f"DASHBOARD : Erreur lors du calcul de la monnaie disponible. Db toute neuve ? : {e}")

