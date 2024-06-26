# Generated by Django 2.2 on 2023-04-06 13:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('epsonprinter', '0005_printer_revoquer_odoo_api_serveur_impression'),
        ('APIcashless', '0157_assets_is_sync'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='cash_float',
            field=models.IntegerField(blank=True, null=True, verbose_name='Fond de caisse par défaut'),
        ),
        migrations.AddField(
            model_name='configuration',
            name='compta_email',
            field=models.EmailField(blank=True, help_text='Email de la compta. Envoie des rapports de la veille en pdf tout les matins.', max_length=254, null=True, verbose_name='Email de la compta.'),
        ),
        migrations.AddField(
            model_name='configuration',
            name='ticketZ_printer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='epsonprinter.Printer'),
        ),
    ]
