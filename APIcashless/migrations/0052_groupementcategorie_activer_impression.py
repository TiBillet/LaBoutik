# Generated by Django 2.2 on 2021-05-24 05:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0051_groupementcategorie_api_serveur_impression'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupementcategorie',
            name='activer_impression',
            field=models.BooleanField(default=False),
        ),
    ]
