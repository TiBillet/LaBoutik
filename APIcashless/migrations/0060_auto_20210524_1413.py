# Generated by Django 2.2 on 2021-05-24 10:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0059_auto_20210524_1057'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupementcategorie',
            name='name',
            field=models.CharField(max_length=50, unique=True),
        ),
    ]
