# Generated by Django 2.2 on 2025-01-28 11:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0249_merge_20250123_0904'),
    ]

    operations = [
        migrations.AlterField(
            model_name='moyenpaiement',
            name='categorie',
            field=models.CharField(choices=[('LE', 'Token local'), ('LG', 'Token cadeau'), ('XE', 'Token exterieur'), ('XG', 'Token exterieur cadeau'), ('FD', 'Fedow'), ('CA', 'Espèces'), ('CC', 'Carte bancaire'), ('CH', 'Chèque'), ('NA', 'Offert'), ('FR', 'Fractionné'), ('CM', 'Commande'), ('AR', 'Ardoise'), ('SN', 'Stripe'), ('SF', 'Token fédéré'), ('OC', 'Oceco'), ('BG', 'Badgeuse'), ('XB', 'Badgeuse fédérée'), ('TP', 'Temps'), ('XT', 'Temps fédéré'), ('AD', 'Adhésion associative'), ('MS', 'Abonnement'), ('XM', 'Abonnement fédéré'), ('FI', 'Points de fidélité'), ('XF', 'Points de fidélité fédérés')], default='LE', max_length=2),
        ),
    ]
