# Generated by Django 2.2 on 2024-01-22 14:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0205_auto_20240122_1830'),
    ]

    operations = [
        migrations.AlterField(
            model_name='moyenpaiement',
            name='place_origin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='moyen_paiements', to='APIcashless.Place'),
        ),
    ]