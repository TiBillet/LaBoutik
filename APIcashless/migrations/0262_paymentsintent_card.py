# Generated by Django 2.2.28 on 2025-07-02 13:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0261_auto_20250623_1701'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentsintent',
            name='card',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payments_intents', to='APIcashless.CarteCashless', verbose_name='Carte cashless'),
        ),
    ]
