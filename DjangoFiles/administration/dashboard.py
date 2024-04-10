from django.utils.translation import ugettext_lazy as _
from jet.dashboard.dashboard import Dashboard
import administration.dashboard_modules as adminDashboard


class CustomIndexDashboard(Dashboard):
    columns = 1

    def init_with_context(self, context):

        self.children.append(adminDashboard.Informations(
            _("Récapitulatif"),
            10,
            column=0,
            order=0
        ))

        self.children.append(adminDashboard.chartMonnaie(
            _("Chiffre d'affaire< 60 jours"),
            10,
            column=0,
            order=0
        ))

        self.children.append(adminDashboard.TempsReel(
            _("Aujourd'hui (>04h00)"),
            column=0,
            order=0
        ))
