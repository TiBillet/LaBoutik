# Generated by Django 2.2 on 2023-02-22 11:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0152_auto_20230210_1443'),
    ]

    operations = [
        migrations.AddField(
            model_name='rapporttableaucomptable',
            name='chiffre_affaire',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
