from django.db import migrations
from APIcashless.models import MoyenPaiement, Configuration, Articles


def add_federated_currency(apps, schema_editor):
    pass
    # MP_Fed, created = MoyenPaiement.objects.get_or_create(name=f"Stripe (Federée)",
    #                                                       is_federated=True,
    #                                                       blockchain=True)
    # config = Configuration.get_solo()
    # config.federated_currency = MP_Fed
    # config.monnaies_acceptes.add(MP_Fed)
    # config.save()
    #
    # print(f"MP_Fed: {MP_Fed} - Created: {created}")
    #
    # recharge_fed, created = Articles.objects.get_or_create(
    #     name="+1",
    #     prix=1,
    #     methode_choices=Articles.RECHARGE_EUROS_FEDERE,
    # )
    #
    # print(f"recharge_fed: {recharge_fed} - Created: {created}")


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('APIcashless', '0142_auto_20221220_1413'),

    ]

    operations = [
        migrations.RunPython(add_federated_currency, reverse),
    ]
