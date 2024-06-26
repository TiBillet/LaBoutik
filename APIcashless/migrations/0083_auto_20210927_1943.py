# Generated by Django 2.2 on 2021-09-27 15:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0082_membre_adhesion_origine'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membre',
            name='adhesion_origine',
            field=models.CharField(choices=[('A', 'Admin'), ('F', 'Front Cashless'), ('Q', 'Scan QR Code'), ('B', 'Billetterie'), ('H', 'HelloAsso')], default='A', max_length=1, verbose_name='Source'),
        ),
        migrations.AlterField(
            model_name='membre',
            name='email',
            field=models.EmailField(blank=True, max_length=50, null=True, unique=True),
        ),
    ]
