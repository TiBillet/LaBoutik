# Generated by Django 2.2 on 2024-02-23 09:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tibiauth', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tibiuser',
            name='public_pem',
            field=models.CharField(blank=True, editable=False, max_length=512, null=True),
        ),
    ]
