# Generated by Django 2.2 on 2021-06-08 06:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0061_configuration_auto_service'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='configuration',
            name='auto_service',
        ),
        migrations.AddField(
            model_name='configuration',
            name='validation_service_ecran',
            field=models.BooleanField(default=True, verbose_name='Validation sur ecran de préparation'),
        ),
    ]
