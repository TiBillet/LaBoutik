from django.core.management.base import BaseCommand, CommandError
from rest_framework_api_key.models import APIKey

from APIcashless.models import MoyenPaiement, Configuration


class Command(BaseCommand):
    help = 'Fedow management. add_asset, remove_asset, list'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('--accept_asset',
                            help='Accept an asset from a FEDOW Federation. Need asset UUID.')

        parser.add_argument('--remove_asset',
                            help='Accept an asset from a FEDOW Federation. Need asset UUID.')

        parser.add_argument('--list', action='store_true',
                            help='List federated assets.')

    def handle(self, *args, **options):
        config = Configuration.get_solo()
        if options.get('accept_asset'):
            try :
                moyen_paiement = MoyenPaiement.objects.get(id=options.get('accept_asset'))
                config.monnaies_acceptes.add(moyen_paiement)
                self.stdout.write(self.style.SUCCESS(
                    f"Asset {moyen_paiement.name} accepted\n"), ending='\n')

            except Exception as e:
                raise CommandError(e)

        if options.get('remove_asset'):
            try :
                moyen_paiement = MoyenPaiement.objects.get(id=options.get('remove_asset'))
                config.monnaies_acceptes.remove(moyen_paiement)
                self.stdout.write(self.style.SUCCESS(
                    f"Asset {moyen_paiement.name} removed\n"), ending='\n')

            except Exception as e:
                raise CommandError(e)


        self.stdout.write(self.style.SUCCESS(f"\n\nAsset actualy accepted : "),ending='\n')

        for mp in config.monnaies_acceptes.all():
            self.stdout.write(self.style.SQL_KEYWORD(f"{mp.name}\n  CURRENCY CODE : {mp.currency_code}\n  UUID : {mp.id}"),ending='\n')


        self.stdout.write(self.style.HTTP_NOT_MODIFIED(f"\n\nAssets available from FEDOW : "),ending='\n')
        for mp in MoyenPaiement.objects.filter(
                blockchain=True,
                is_federated=True,
        ):
            self.stdout.write(self.style.SQL_KEYWORD(f"{mp.name}\n  CURRENCY CODE : {mp.currency_code}\n  UUID : {mp.id}"),ending='\n')
