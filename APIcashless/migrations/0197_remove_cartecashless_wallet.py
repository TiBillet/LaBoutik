# Generated by Django 2.2 on 2023-12-22 11:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0196_auto_20231222_1418'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cartecashless',
            name='wallet',
        ),
    ]
