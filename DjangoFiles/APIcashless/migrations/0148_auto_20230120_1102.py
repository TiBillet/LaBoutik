# Generated by Django 2.2 on 2023-01-20 07:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0147_auto_20230111_0845'),
    ]

    operations = [
        migrations.AlterField(
            model_name='articlevendu',
            name='qty',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='moyenpaiement',
            name='categorie',
            field=models.CharField(choices=[('LE', 'Token local €'), ('LG', 'Token local cadeau'), ('AR', 'Ardoise'), ('SF', 'Token Federated Stripe'), ('SN', 'Stripe no federated'), ('CA', 'Espèces'), ('CC', 'Carte bancaire TPE'), ('OC', 'Oceco')], default='LE', max_length=2),
        ),
    ]