# Generated by Django 2.2 on 2021-05-13 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0041_configuration_serveur_cups'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='groupementcategorie',
            name='thermal_printer_ip',
        ),
        migrations.AddField(
            model_name='groupementcategorie',
            name='thermal_printer_adress',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name="Adresse ip de l'imprimante CUPS"),
        ),
    ]
