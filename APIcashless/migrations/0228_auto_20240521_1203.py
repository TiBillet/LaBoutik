# Generated by Django 2.2 on 2024-05-21 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0227_auto_20240515_1143'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuration',
            name='numero_tva',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]