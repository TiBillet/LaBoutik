import os

from django.conf import settings
from django.core.management import BaseCommand
from fedow_connect.fedow_api import FedowAPI
from APIcashless.models import Configuration, MoyenPaiement


class Command(BaseCommand):
    def handle(self, *args, **options):
        config = Configuration.get_solo()
        if config.can_fedow():
            fedowAPI = FedowAPI()
            # Le serializer valide les assets de fedow et les créé s'ils n'existent pas.
            fedowAPI.place.get_accepted_assets()
            if settings.TEST:
                external_assets = MoyenPaiement.objects.filter(categorie__in=[
                    MoyenPaiement.EXTERIEUR_FED,
                    MoyenPaiement.EXTERIEUR_GIFT,
                    MoyenPaiement.STRIPE_FED,
                    MoyenPaiement.EXTERNAL_BADGE,
                    MoyenPaiement.EXTERNAL_MEMBERSHIP,
                ])
                for mp in external_assets:
                    config.monnaies_acceptes.add(mp)
                    print(f"Monnaie ajoutée à la config : {mp}")
                config.save()
