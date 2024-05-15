# Generated by Django 2.2 on 2023-08-25 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FedowNodeConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enc_private_key', models.CharField(editable=False, max_length=2048)),
                ('public_key', models.CharField(editable=False, max_length=512)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]