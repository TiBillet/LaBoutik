# Generated by Django 2.2 on 2021-04-17 09:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0024_auto_20210416_1413'),
    ]

    operations = [
        migrations.AddField(
            model_name='pointdevente',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='points_de_ventes', to='APIcashless.Categorie', verbose_name='categories'),
        ),
    ]
