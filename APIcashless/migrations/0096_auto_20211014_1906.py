# Generated by Django 2.2 on 2021-10-14 15:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0095_rapportarticlesvendu_pos'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='rapporttableaucomptable',
            options={'ordering': ('-date',), 'verbose_name': 'Tableau comptable', 'verbose_name_plural': 'Tableaux comptable'},
        ),
        migrations.AlterField(
            model_name='membre',
            name='paiment_adhesion',
            field=models.CharField(choices=[('E', 'Espece'), ('C', 'CB'), ('G', 'Gratuit'), ('N', 'Adhérer plus tard')], default='N', max_length=1, verbose_name='Methode de paiement'),
        ),
    ]
