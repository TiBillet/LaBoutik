# Generated by Django 2.2 on 2024-12-14 19:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0246_articlevendu_comment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuration',
            name='void_card',
            field=models.BooleanField(default=True, help_text="Si coché, la carte vidée redeviendra neuve. Sinon, la carte garde toujours le portefeuille de l'utilisateur pour par exemple ses adhésions.", verbose_name="Séparer l'utilisateur lors du vider carte"),
        ),
    ]
