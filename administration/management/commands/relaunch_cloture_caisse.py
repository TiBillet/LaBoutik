from django.utils import timezone
from datetime import datetime
from APIcashless.models import ArticleVendu, Configuration, Categorie, Articles, RapportTableauComptable, ClotureCaisse
from dateutil.relativedelta import relativedelta
from APIcashless.tasks import GetOrCreateRapportFromDate

now = timezone.localtime()
config = Configuration.get_solo()
heure_cloture = config.cloture_de_caisse_auto

# Les Cashback sont compte comme MP Stripe, on corrige :
ArticleVendu.objects.filter(article__methode_choices=Articles.RECHARGE_CADEAU).update(
    moyen_paiement=None)

# Update pour les articles sans catégories
avs = ArticleVendu.objects.filter(article__methode_choices=Articles.VENTE).order_by('-date_time')
categorie, created = Categorie.objects.get_or_create(name="Autre")

# si les tva on bougé :
avs.filter(categorie__isnull=True).update(categorie=categorie)
list_art_sans_tva = set(avs.filter(tva=0, categorie__tva__isnull=False).values_list('categorie', flat=True).distinct())
for categorie in list_art_sans_tva :
    cat = Categorie.objects.get(pk=categorie)
    avs.filter(tva=0, categorie=cat).update(tva=cat.tva.taux)

# Lancement des rapports mensuels depuis le début :
premiere_vente = timezone.localtime(avs.last().date_time)
premier_du_mois = premiere_vente.date().replace(day=1)
premiere_ouverture = timezone.make_aware(datetime.combine(premier_du_mois, heure_cloture))

# nbr_mois_anciennete = relativedelta(now, premiere_ouverture).months + (relativedelta(now, premiere_ouverture).year * 12)
nbr_mois_anciennete = 24

# Calcul des raports et ticket z de chaque mois depuis le début :
start = premiere_ouverture
for i in range(nbr_mois_anciennete):
    end = premiere_ouverture + relativedelta(months=i + 1)
    print(start, end)
    GetOrCreateRapportFromDate((start.isoformat(), end.isoformat()))
    start = end

# Calcul des rapport du 1er janvier
GetOrCreateRapportFromDate(('2023-01-01T04:00:00+04:00', '2024-01-01T04:00:00+04:00'))
GetOrCreateRapportFromDate(('2022-01-01T04:00:00+04:00', '2023-01-01T04:00:00+04:00'))
GetOrCreateRapportFromDate(('2021-01-01T04:00:00+04:00', '2022-01-01T04:00:00+04:00'))
GetOrCreateRapportFromDate(('2020-01-01T04:00:00+04:00', '2021-01-01T04:00:00+04:00'))
GetOrCreateRapportFromDate(('2019-01-01T04:00:00+04:00', '2020-01-01T04:00:00+04:00'))


# Remplacement des tableaux comptable quotidien par des Clotures de caisses
xrapports = RapportTableauComptable.objects.all()
for rapport in xrapports:
    start = timezone.make_aware(datetime.combine(rapport.date, heure_cloture))
    end = start + relativedelta(days=1)
    GetOrCreateRapportFromDate((start.isoformat(), end.isoformat()))


#### OR
couple_de_date = []
all_cloture = ClotureCaisse.objects.all()
for cloture in all_cloture:
    couple_de_date.append((cloture.start, cloture.end))

ClotureCaisse.objects.all().delete()
for couple in couple_de_date:
    GetOrCreateRapportFromDate(couple)

