# Generated by Django 2.2 on 2023-01-02 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0145_auto_20230102_1615'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuration',
            name='domaine_cashless',
            field=models.URLField(default='https://demo.cashless.tibillet.localhost/'),
        ),
    ]
