# Generated by Django 2.2 on 2021-05-24 06:56

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0057_commandesauvegarde_numero_du_ticket_imprime'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commandesauvegarde',
            name='numero_du_ticket_imprime',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
        ),
    ]
