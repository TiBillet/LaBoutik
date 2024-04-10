from django.core.management.base import BaseCommand
import uuid, random
from uuid import uuid4
from APIcashless.models import Membre, CarteCashless, Origin, MoyenPaiement, Assets


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        origin = Origin.objects.get_or_create(generation=1)[0]
        # !pip install Faker
        # noinspection PyUnresolvedReferences
        from faker import Faker
        for i in range(100):
            fake = Faker()
            fake_uuid = str(uuid4())
            card, created = CarteCashless.objects.get_or_create(
                tag_id=str(uuid4()).split('-')[0].upper(),
                uuid_qrcode=fake_uuid,
                number=fake_uuid.split('-')[0],
                origin=origin,
                membre=Membre.objects.create(name=fake.name(), email=fake.email()),
            )

            mp_primary = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_EURO)
            mp_gift = MoyenPaiement.objects.get(categorie=MoyenPaiement.LOCAL_GIFT)

            asset_primary = Assets.objects.create(
                qty=random.randint(0, 100),
                carte=card,
                monnaie=mp_primary,
            )
            asset_gift = Assets.objects.create(
                qty=random.randint(0, 100),
                carte=card,
                monnaie=mp_gift,
            )
