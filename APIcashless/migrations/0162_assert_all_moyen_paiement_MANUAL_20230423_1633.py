# Generated by Django 2.2 on 2023-04-23 12:33

from django.db import migrations
from django.core.management import call_command


def migrate_assert_mp_solo(apps, schema_editor):
    pass
    # call_command('assert_mp_solo')


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('APIcashless', '0161_Moyen_de_paiement_categorie_MANUAL'),
    ]

    operations = [
        migrations.RunPython(migrate_assert_mp_solo, reverse),
    ]
