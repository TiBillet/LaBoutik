# Generated by Django 2.2 on 2024-02-01 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0212_auto_20240131_1401'),
    ]

    operations = [
        migrations.AlterField(
            model_name='moyenpaiement',
            name='categorie',
            field=models.CharField(choices=[('LE', 'Token local €'), ('LG', 'Token local cadeau'), ('FR', 'Fractionné'), ('SF', 'Stripe'), ('XE', 'Token fédéré exterieur €'), ('XG', 'Token fédéré cadeau'), ('FD', 'Fedow'), ('SN', 'Web (Stripe)'), ('CA', 'Espèces'), ('CC', 'Carte bancaire'), ('CH', 'Cheque'), ('OC', 'Oceco'), ('AR', 'Ardoise'), ('CM', 'Commande'), ('BG', 'Badgeuse'), ('XB', 'Badgeuse fédérée'), ('TP', 'Temps'), ('XT', 'Temps fédéré'), ('AD', 'Adhésion associative'), ('MS', 'Abonnement'), ('XM', 'Abonnement fédéré'), ('FI', 'Points de fidélité'), ('XF', 'Points de fidélité fédérés')], default='LE', max_length=2),
        ),
    ]
