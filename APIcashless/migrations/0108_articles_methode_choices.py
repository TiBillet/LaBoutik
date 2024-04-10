# Generated by Django 2.2 on 2022-02-17 06:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0107_auto_20211209_1444'),
    ]

    operations = [
        migrations.AddField(
            model_name='articles',
            name='methode_choices',
            field=models.CharField(choices=[('VT', 'Vente'), ('RS', 'RechargeS'), ('RE', 'Recharge €'), ('RC', 'Recharge Cadeau'), ('AD', 'Adhésions'), ('CR', 'Retour de consigne'), ('VC', 'Vider Carte'), ('BC', 'Vider Carte'), ('VV', 'Vider Carte'), ('FR', 'Fractionné')], default='VT', max_length=2),
        ),
    ]
