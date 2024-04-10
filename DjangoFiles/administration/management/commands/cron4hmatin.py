from django.utils import timezone
from APIcashless.models import CommandeSauvegarde, Table, Configuration, GroupementCategorie
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from APIcashless.tasks import GetOrCreateRapportFromDate
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def archive_commande(self):
        # archive les commandes servie et payée :
        for commande in CommandeSauvegarde.objects.filter(archive=False, statut__in=[CommandeSauvegarde.SERVIE_PAYEE,
                                                                                     CommandeSauvegarde.ANNULEE]):
            commande.archive = True
            commande.save()

    def table_ephemere(self):
        # table ephemere archivée si libre
        for table in Table.objects.all():
            if table.ephemere and table.statut == Table.LIBRE:
                table.archive = True
                table.save()

    def rezet_compteur_ticket_journee(self):
        for group in GroupementCategorie.objects.all():
            group.compteur_ticket_journee = 0
            group.save()

    # def calcul_rapport_veille(self):
    #     # on calcule la date du jour, c’est-à-dire jusqu’au lendemain à 4 h du mat'
    #     jour = timezone.localdate() - timedelta(days=1)
    #
    #     try:
    #         # Génération du ticket Z via le thread celery
    #         rapport = RapportTableauComptable.objects.get(date=jour)
    #         task = ticketZ_fromRapport_to_mail.delay(rapport.pk)
    #
    #     except RapportTableauComptable.DoesNotExist:
    #         logger.info(f"CRON 4h du matin : Pas de tableau pour le jour {jour}")
    #     except Exception as e:
    #         logger.error(f"CRON 4h du matin : Exception : {e}")
    #         raise e

    def calculs_des_rapports_et_ticketZ(self):
        config = Configuration.get_solo()
        heure_cloture = config.cloture_de_caisse_auto

        now = timezone.localtime()
        iso_calendar = now.isocalendar()

        # Tout les jours
        jour_4h = timezone.make_aware(datetime.combine(now, heure_cloture))
        hier_4h = jour_4h - relativedelta(days=1)
        start = timezone.make_aware(datetime.combine(hier_4h, heure_cloture))
        end = timezone.make_aware(datetime.combine(jour_4h, heure_cloture))

        # TODO: Si la cloture de caisse n'a pas enore été faite
        GetOrCreateRapportFromDate.delay((start.isoformat(), end.isoformat()))

        # Chaque lundi matin :
        if now.weekday() == 0:
            ce_lundi = datetime.fromisocalendar(iso_calendar[0], iso_calendar[1], 1)
            lundi_precedent = ce_lundi - relativedelta(weeks=1)

            start = timezone.make_aware(datetime.combine(lundi_precedent, heure_cloture))
            end = timezone.make_aware(datetime.combine(ce_lundi, heure_cloture))

            GetOrCreateRapportFromDate.delay((start.isoformat(), end.isoformat()))

        # Chaque premier du mois
        if now.day == 1:
            prems_du_mois = datetime(now.year, now.month, 1)
            prems_du_mois_precedent = prems_du_mois - relativedelta(months=1)

            start = timezone.make_aware(datetime.combine(prems_du_mois_precedent, heure_cloture))
            end = timezone.make_aware(datetime.combine(prems_du_mois, heure_cloture))

            GetOrCreateRapportFromDate.delay((start.isoformat(), end.isoformat()))

        # Chaque 1er de l'an
        if now.day == 1 and now.month == 1:
            prems_year = datetime(now.year, 1, 1)
            last_year = prems_year - relativedelta(years=1)

            start = timezone.make_aware(datetime.combine(last_year, heure_cloture))
            end = timezone.make_aware(datetime.combine(prems_year, heure_cloture))

            GetOrCreateRapportFromDate.delay((start.isoformat(), end.isoformat()))

    def handle(self, *args, **options):
        # self.calcul_rapport_veille()
        self.table_ephemere()
        self.archive_commande()
        self.calculs_des_rapports_et_ticketZ()
        self.rezet_compteur_ticket_journee()
