import json
from APIcashless.models import CarteCashless, Membre
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder


class Command(BaseCommand):
    def handle(self, *args, **options):
        data = []
        for membre in Membre.objects.filter(email__isnull=False).exclude(email=""):
            data.append(
                {
                    'email': membre.email,
                    'first_name': membre.prenom,
                    'last_name': membre.name,
                    'postal_code': membre.code_postal,
                    'date_added': membre.date_ajout,
                    'last_contribution': membre.date_derniere_cotisation,
                    'cotisation': membre.cotisation,
                    'card_qrcode_uuid': [f"{carte.uuid_qrcode}" for carte in membre.CarteCashless_Membre.all() ]
                }
            )
        with open('memberships.json', 'w') as f:
            json.dump(data, f, cls=DjangoJSONEncoder)

        # Pour importer :
        # import json
        # with open('memberships.json', 'r', encoding='utf-8') as readf:
        #     loaded_data = json.load(readf)