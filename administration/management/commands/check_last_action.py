from django.core.management import BaseCommand

from APIcashless.models import Assets, Membre

class Command(BaseCommand):

    def handle(self, *args, **options):

        assets = Assets.objects.all()
        if len(assets) > 0 :
            for asset in assets:
                if not asset.monnaie.cadeau:
                    if asset.carte.membre:
                        Membre.objects.filter(id=asset.carte.membre.id).update(last_action=asset.last_date_used)

            membres_sans_carte = Membre.objects.filter(CarteCashless_Membre=None)
            for membre in membres_sans_carte:
                Membre.objects.filter(id=membre.id).update(last_action=membre.date_ajout)
