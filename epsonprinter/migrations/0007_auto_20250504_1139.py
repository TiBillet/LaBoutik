# Generated by Django 2.2.28 on 2025-05-04 09:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('epsonprinter', '0006_printer_host'),
    ]

    operations = [
        migrations.RenameField(
            model_name='printer',
            old_name='revoquer_odoo_api_serveur_impression',
            new_name='revoquer_api_serveur_impression',
        ),
        migrations.AddField(
            model_name='printer',
            name='printer_type',
            field=models.CharField(choices=[('EP', 'Epson via Serveur sur Pi (réseau ou USB, 80mm)'), ('S8', 'Imprimante intégrée aux Sunmi 80mm de large'), ('S5', 'Imprimante intégrée aux Sunmi 57mm de large'), ('SC', 'NT311 Sunmi cloud printer 80mm')], default='EP', max_length=2, verbose_name="Type d'imprimante"),
        ),
        migrations.AddField(
            model_name='printer',
            name='sunmi_serial_number',
            field=models.CharField(blank=True, help_text='Vérifiez sur votre interface https://partner.sunmi.com et comparez sur le ticket de test.', max_length=100, null=True, verbose_name="Numéro de série de l'imprimante Sunmi Cloud Printing"),
        ),
        migrations.AlterField(
            model_name='printer',
            name='host',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='printers', to='APIcashless.Appareil', verbose_name='Appareil hôte'),
        ),
    ]
