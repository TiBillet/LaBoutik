# Generated by Django 2.2 on 2021-09-02 12:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0077_rapportarticlesvendu_total_benefice_estime'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='articlevendu',
            options={'ordering': ('-date_time',), 'verbose_name': 'Detail par article vendus', 'verbose_name_plural': 'Detail par article vendus'},
        ),
    ]