# Generated by Django 2.2 on 2024-11-20 10:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0239_auto_20241031_1645'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='void_card',
            field=models.BooleanField(default=False, help_text="Si coché, la carte vidée redeviendra neuve. Sinon, la carte garde toujours le portefeuille de l'utilisateur pour par exemple ses adhésions.", verbose_name="Séparer l'utilisateur lors du vider carte"),
        ),
    ]
