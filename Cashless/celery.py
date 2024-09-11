import os

from celery import Celery
from celery.signals import setup_logging
from celery.schedules import crontab
from django.conf import settings
from django.utils import timezone
import logging
from django.core.management import call_command
logger = logging.getLogger(__name__)

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Cashless.settings')

app = Celery('Cashless')
app.conf.timezone = os.environ.get('TIME_ZONE', 'Europe/Paris')
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
# app.autodiscover_tasks()
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request}')


@setup_logging.connect
def config_loggers(*args, **kwags):
    from logging.config import dictConfig
    from django.conf import settings
    dictConfig(settings.LOGGING)

@app.task
def add(x, y):
    return x + y



@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    # sender.add_periodic_task(10.0, periodic_test.s(f'{timezone.now()} - hello 10'), name='add every 10')
    # sender.add_periodic_task(10.0, cron_morning.s(), name='add every 10')

    # Calls test('hello') every 30 seconds.
    # It uses the same signature of previous task, an explicit name is
    # defined to avoid this task replacing the previous one defined.
    # sender.add_periodic_task(30.0, periodic_test.s(f'{timezone.now()} - hello 30'), name='add every 30')

    # Calls test('world') every 30 seconds
    # sender.add_periodic_task(30.0, periodic_test.s('world'), expires=10)

    # doc : https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html#crontab-schedules
    logger.info(f'setup_periodic_tasks cron_morning at 7AM')
    sender.add_periodic_task(
        crontab(hour=7, minute=0),
        cron_morning.s(),
    )
    logger.info(f'setup_periodic_tasks DONE')


@app.task
def periodic_test(arg):
    logger.info(f'{arg} periodic task')
    with open('/DjangoFiles/Backup/backup.log', 'w') as f:
        f.write(f'{arg}\n')
        f.close()

    print(arg)

@app.task
def cron_morning():
    logger.info(f'call_command cron_morning START')
    call_command('cron_morning')
    logger.info(f'call_command cron_morning END')
