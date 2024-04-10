from django.core.management.base import BaseCommand

from APIcashless.models import Configuration, MoyenPaiement, Origin, Place


class Command(BaseCommand):
    def handle(self, *args, **options):
        config = Configuration.get_solo()
        config.stripe_connect_account = None
        config.stripe_connect_valid = False
        config.onboard_url = None
        config.string_connect = None
        config.fedow_domain = None
        config.fedow_place_uuid = None
        config.fedow_place_admin_apikey = None
        config.fedow_place_wallet_uuid = None
        config.save()

        Origin.objects.all().delete()
        Place.objects.all().delete()
        MoyenPaiement.objects.filter(categorie=MoyenPaiement.STRIPE_FED).delete()