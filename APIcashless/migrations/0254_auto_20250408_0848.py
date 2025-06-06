# Generated by Django 2.2 on 2025-04-08 06:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0253_auto_20250331_1657'),
    ]

    operations = [
        migrations.AlterField(
            model_name='articles',
            name='methode_choices',
            field=models.CharField(choices=[('VT', 'Vente'), ('RE', 'Recharge €'), ('RC', 'Recharge Cadeau'), ('TM', 'Recharge Temps'), ('AD', 'Adhésions'), ('CR', 'Retour de consigne'), ('VC', 'Vider Carte'), ('VV', 'Void Carte'), ('FR', 'Fractionné'), ('BI', 'Billet de concert'), ('BG', 'Badgeuse'), ('FD', 'Fidélité'), ('HB', 'Cashback'), ('TR', 'Virement bancaire')], default='VT', max_length=2, verbose_name='methode'),
        ),
    ]
