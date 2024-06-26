# Generated by Django 2.2 on 2023-11-16 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0190_origin_place'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='private_pem',
            field=models.CharField(default='', editable=False, max_length=2048),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='configuration',
            name='public_pem',
            field=models.CharField(default='', editable=False, max_length=512),
            preserve_default=False,
        ),
    ]
