# Generated by Django 2.2 on 2024-05-27 13:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0230_auto_20240527_1509'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuration',
            name='fidelity_asset_trigger',
            field=models.ManyToManyField(blank=True, related_name='fidelity_asset_trigger', to='APIcashless.MoyenPaiement', verbose_name="Asset déclencheur de l'incrémentation des points de fidélité"),
        ),
    ]
