# Generated by Django 2.2 on 2022-08-18 15:58

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0125_auto_20220817_1329'),
    ]

    operations = [
        migrations.AddField(
            model_name='articlevendu',
            name='uuid_paiement',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
