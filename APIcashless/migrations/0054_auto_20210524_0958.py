# Generated by Django 2.2 on 2021-05-24 05:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0053_auto_20210524_0908'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupementcategorie',
            name='qty_ticket',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='Nombre de copie de ticket à imprimmer'),
        ),
        migrations.AlterField(
            model_name='configuration',
            name='activer_impression',
            field=models.BooleanField(default=False, verbose_name="Activer l'impression. ( Voir dans les groupements de préparation pour la configuration )"),
        ),
    ]
