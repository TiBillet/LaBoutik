# Generated by Django 2.2 on 2022-03-26 14:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0109_auto_20220217_1048'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='odoo_api_key',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='configuration',
            name='odoo_url',
            field=models.URLField(blank=True, null=True, verbose_name='Url du serveur odoo'),
        ),
        migrations.AlterField(
            model_name='articles',
            name='methode_choices',
            field=models.CharField(choices=[('VT', 'Vente'), ('RS', 'RechargeS'), ('RE', 'Recharge €'), ('RC', 'Recharge Cadeau'), ('AD', 'Adhésions'), ('CR', 'Retour de consigne'), ('VC', 'Vider Carte'), ('BC', 'Blanchir Carte'), ('VV', 'Void Carte'), ('FR', 'Fractionné')], default='VT', max_length=2),
        ),
    ]
