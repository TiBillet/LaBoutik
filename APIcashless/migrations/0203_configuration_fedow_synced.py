# Generated by Django 2.2 on 2024-01-05 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0202_auto_20240103_0001'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='fedow_synced',
            field=models.BooleanField(default=False, editable=False),
        ),
    ]
