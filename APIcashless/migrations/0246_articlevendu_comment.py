# Generated by Django 2.2 on 2024-12-10 05:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0245_auto_20241129_1009'),
    ]

    operations = [
        migrations.AddField(
            model_name='articlevendu',
            name='comment',
            field=models.TextField(blank=True, null=True, verbose_name='Commentaire'),
        ),
    ]
