# Generated by Django 2.2 on 2021-05-06 09:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0032_auto_20210506_0942'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='pointdevente',
            options={'ordering': ('poid_liste', 'name'), 'verbose_name': 'Point de vente', 'verbose_name_plural': 'Points de vente'},
        ),
        migrations.AlterField(
            model_name='categorie',
            name='poid_liste',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Poids'),
        ),
        migrations.AlterField(
            model_name='configuration',
            name='fuseau_horaire',
            field=models.CharField(choices=[('Indian/Reunion', 'Indian/Reunion'), ('Europe/Paris', 'Europe/Paris')], default='Indian/Reunion', max_length=50),
        ),
        migrations.AlterField(
            model_name='pointdevente',
            name='poid_liste',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Poids'),
        ),
    ]
