# Generated by Django 2.2 on 2021-04-09 07:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0006_auto_20210409_1130'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pointdevente',
            name='articles',
            field=models.ManyToManyField(blank=True, related_name='points_de_ventes', to='APIcashless.Articles', verbose_name='articles'),
        ),
    ]
