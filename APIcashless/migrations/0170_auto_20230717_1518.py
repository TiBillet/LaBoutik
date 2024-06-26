# Generated by Django 2.2 on 2023-07-17 11:18

from django.db import migrations, models
from django.core.management import call_command

def check_permission(apps, schema_editor):
    call_command('check_permissions')

def reverse(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0169_auto_20230715_1918'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuration',
            name='cash_float',
            field=models.IntegerField(default=0, verbose_name='Fond de caisse par défaut'),
        ),
        migrations.RunPython(check_permission, reverse),
    ]
