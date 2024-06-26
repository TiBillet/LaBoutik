# Generated by Django 2.2 on 2021-04-09 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0012_auto_20210409_1149'),
    ]

    operations = [
        migrations.AddField(
            model_name='articlecommandesauvegarde',
            name='reste_a_payer',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='articlecommandesauvegarde',
            name='reste_a_servir',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='articlecommandesauvegarde',
            name='statut',
            field=models.CharField(choices=[('PP', 'En préparation'), ('PR', 'Prêt à servir'), ('SV', 'Servis'), ('PY', 'Payés'), ('SP', 'Servis et payés')], default='PP', max_length=2),
        ),
        migrations.AlterField(
            model_name='articlecommandesauvegarde',
            name='qty',
            field=models.FloatField(),
        ),
    ]
