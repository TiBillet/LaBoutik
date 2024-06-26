# Generated by Django 2.2 on 2021-04-09 07:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0009_auto_20210409_1133'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartecashless',
            name='uuid_qrcode',
            field=models.UUIDField(blank=True, null=True, verbose_name='Uuid'),
        ),
        migrations.AlterField(
            model_name='cartecashless',
            name='number',
            field=models.CharField(blank=True, db_index=True, max_length=8, null=True, unique=True),
        ),
    ]
