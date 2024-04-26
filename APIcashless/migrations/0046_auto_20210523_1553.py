# Generated by Django 2.2 on 2021-05-23 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0045_auto_20210517_1128'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='api_print',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name="Clé d'api pour serveur d'impression"),
        ),
        migrations.AlterField(
            model_name='configuration',
            name='serveur_cups',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name="Adresse du serveur d'impression ( https://<ip>:<port> )"),
        ),
    ]
