# Generated by Django 2.2 on 2021-10-21 11:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('APIcashless', '0097_auto_20211018_0831'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='url_image',
            field=models.URLField(blank=True, null=True),
        ),
    ]