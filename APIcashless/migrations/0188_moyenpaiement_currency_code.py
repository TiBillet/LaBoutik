# Generated by Django 2.2 on 2023-10-23 09:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0187_configuration_fedow_place_wallet_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='moyenpaiement',
            name='currency_code',
            field=models.CharField(blank=True, max_length=3, null=True),
        ),
    ]
