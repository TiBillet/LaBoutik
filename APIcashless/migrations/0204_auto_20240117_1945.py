# Generated by Django 2.2 on 2024-01-17 15:45

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0203_configuration_fedow_synced'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuration',
            name='cloture_de_caisse_auto',
            field=models.TimeField(blank=True, default=datetime.time(4, 0), null=True, verbose_name='Heure de cloture automatique de toutes les caisses'),
        ),
    ]
