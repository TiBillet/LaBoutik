# Generated by Django 2.2 on 2023-10-11 07:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fedow_connect', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='fedownodeconfig',
            old_name='enc_private_key',
            new_name='private_pem',
        ),
        migrations.RenameField(
            model_name='fedownodeconfig',
            old_name='public_key',
            new_name='public_pem',
        ),
    ]
