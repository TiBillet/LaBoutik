# Generated by Django 2.2 on 2022-09-22 11:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0129_auto_20220922_1457'),
    ]

    operations = [
        migrations.AlterField(
            model_name='articles',
            name='prix',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True, verbose_name='Prix de vente'),
        ),
        migrations.AlterField(
            model_name='articles',
            name='prix_achat',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True, verbose_name="Prix d'achat"),
        ),
        migrations.AlterField(
            model_name='articlevendu',
            name='prix',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='articlevendu',
            name='qty',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='assets',
            name='qty',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='configuration',
            name='taux_tva',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='configuration',
            name='valeur_oceco',
            field=models.DecimalField(decimal_places=2, default=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name='creditexterieur',
            name='qty',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='informationgenerale',
            name='total_monnaie_principale',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='membre',
            name='cotisation',
            field=models.DecimalField(decimal_places=2, default=20, help_text='Vous pouvez modifier la valeur par default dans la page de configuration générale', max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapportarticlesvendu',
            name='carte_bancaire',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='CB'),
        ),
        migrations.AlterField(
            model_name='rapportarticlesvendu',
            name='espece',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapportarticlesvendu',
            name='mollie',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Web (mollie)'),
        ),
        migrations.AlterField(
            model_name='rapportarticlesvendu',
            name='monnaie_principale',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Cashless'),
        ),
        migrations.AlterField(
            model_name='rapportarticlesvendu',
            name='monnaie_principale_cadeau',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapportarticlesvendu',
            name='oceco',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapportarticlesvendu',
            name='total_benefice_estime',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='adhesion_carte_bancaire',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='adhesion_espece',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='adhesion_stripe',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='benefice_estime',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='cadeau_restant',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='cadeau_restant_calcul_rapport',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='cout_estime',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='delta_cadeau',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='delta_monnaie',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='monnaie_restante',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='monnaie_restante_calcul_rapport',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='recharge_cadeau',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='recharge_cadeau_oceco',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='recharge_cashless_carte_bancaire',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='recharge_cashless_espece',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='recharge_cashless_stripe',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='remboursement_carte_bancaire',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='remboursement_espece',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='remboursement_stripe',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='vente_directe_carte_bancaire',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='vente_directe_espece',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable',
            name='vente_directe_stripe',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='rapporttableaucomptable_pos',
            name='depense',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
