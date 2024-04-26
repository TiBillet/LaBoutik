# Generated by Django 2.2 on 2021-10-05 07:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0084_auto_20211005_0942'),
    ]

    operations = [
        migrations.CreateModel(
            name='RapportTableauComptable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('recharge_cashless_carte_bancaire', models.FloatField(default=0)),
                ('recharge_cashless_espece', models.FloatField(default=0)),
                ('recharge_cashless_stripe', models.FloatField(default=0)),
                ('vente_directe_carte_bancaire', models.FloatField(default=0)),
                ('vente_directe_espece', models.FloatField(default=0)),
                ('vente_directe_stripe', models.FloatField(default=0)),
                ('remboursement_carte_bancaire', models.FloatField(default=0)),
                ('remboursement_espece', models.FloatField(default=0)),
                ('remboursement_stripe', models.FloatField(default=0)),
                ('recharge_cadeau', models.FloatField(default=0)),
                ('recharge_cadeau_oceco', models.FloatField(default=0)),
                ('monnaie_restante', models.FloatField(default=0)),
                ('delta_monnaie', models.FloatField(default=0)),
                ('cadeau_restant', models.FloatField(default=0)),
                ('delta_cadeau', models.FloatField(default=0)),
                ('benefice_estime', models.FloatField(default=0)),
            ],
        ),
        migrations.AlterField(
            model_name='articlecommandesauvegarde',
            name='reste_a_servir',
            field=models.FloatField(default=0),
        ),
        migrations.CreateModel(
            name='RapportTableauComptable_POS',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('depense', models.FloatField(default=0)),
                ('monnaie', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='APIcashless.Assets')),
                ('pos', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='APIcashless.PointDeVente')),
                ('rapport', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='depenses_par_POS', to='APIcashless.RapportTableauComptable')),
            ],
        ),
    ]
