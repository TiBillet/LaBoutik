# Generated by Django 2.2 on 2021-10-18 04:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('APIcashless', '0096_auto_20211014_1906'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='articlevendu',
            name='user',
        ),
        migrations.CreateModel(
            name='IpUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.GenericIPAddressField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='articlevendu',
            name='ip_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='APIcashless.IpUser'),
        ),
    ]
