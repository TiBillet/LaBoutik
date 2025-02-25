# Generated by Django 2.2 on 2024-11-28 12:52

from django.db import migrations, models
import django.db.models.deletion


def add_fedow_asset_to_article(apps, schema_editor):
    MoyenPaiement = apps.get_model('APIcashless', 'MoyenPaiement')
    Articles = apps.get_model('APIcashless', 'Articles')
    if MoyenPaiement.objects.filter(categorie='LE').exists() and MoyenPaiement.objects.filter(
            categorie='LG').exists():
        Articles.objects.filter(methode_choices='RE').update(
            fedow_asset=MoyenPaiement.objects.get(categorie='LE')
        )

        Articles.objects.filter(methode_choices='RC').update(
            fedow_asset=MoyenPaiement.objects.get(categorie=('LG'))
        )


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('APIcashless', '0243_auto_20241126_1702'),
    ]

    operations = [
        migrations.AlterField(
            model_name='articles',
            name='direct_to_printer',
            field=models.ForeignKey(blank=True,
                                    help_text='Activez pour une impression directe après chaque vente. Utile pour vendre des billets.',
                                    null=True, on_delete=django.db.models.deletion.SET_NULL, to='epsonprinter.Printer'),
        ),
        migrations.AlterField(
            model_name='articles',
            name='fedow_asset',
            field=models.ForeignKey(blank=True,
                                    help_text='Asset Fédéré. Obligatoire pour cashless, adhésion ou badgeuse.',
                                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='subscription_articles', to='APIcashless.MoyenPaiement',
                                    verbose_name='Asset Fédéré. Obligatoire pour cashless, adhésion ou badgeuse.'),
        ),
        migrations.AlterField(
            model_name='articles',
            name='methode_choices',
            field=models.CharField(
                choices=[('VT', 'Vente'), ('RE', 'Recharge €'), ('RC', 'Recharge Cadeau'), ('TM', 'Recharge Temps'),
                         ('AD', 'Adhésions'), ('CR', 'Retour de consigne'), ('VC', 'Vider Carte'), ('VV', 'Void Carte'),
                         ('FR', 'Fractionné'), ('BI', 'Billet de concert'), ('BG', 'Badgeuse'), ('FD', 'Fidélité'),
                         ('HB', 'Cashback')], default='VT', max_length=2, verbose_name='methode'),
        ),
        migrations.RunPython(add_fedow_asset_to_article, reverse),
    ]
