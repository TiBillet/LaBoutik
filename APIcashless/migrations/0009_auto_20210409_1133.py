# Generated by Django 2.2 on 2021-04-09 07:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0008_auto_20210409_1133'),
    ]

    operations = [
        migrations.AddField(
            model_name='articles',
            name='fractionne',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='articles',
            name='archive',
            field=models.BooleanField(default=False, verbose_name='Archiver'),
        ),
    ]
