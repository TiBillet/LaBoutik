# Generated by Django 2.2 on 2024-04-02 10:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0222_auto_20240226_1152'),
    ]

    operations = [
        migrations.AddField(
            model_name='appareil',
            name='apk_version',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='appareil',
            name='hostname',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
