#!/bin/bash
set -e

# mkdir /root/.ssh
# touch /root/.ssh/known_hosts
# ssh-keyscan backup.server >> /root/.ssh/known_hosts

#crontab /DjangoFiles/cron/cron
#service cron start

mkdir -p /DjangoFiles/www
touch /DjangoFiles/www/nginxAccess.log
touch /DjangoFiles/www/nginxError.log

cd /DjangoFiles

poetry run python manage.py collectstatic --noinput
poetry run python manage.py migrate
poetry run python manage.py popdb --test

sleep infinity

#poetry run python manage.py runserver 0.0.0.0:8000
#gunicorn Cashless.wsgi --log-level=debug --log-file /DjangoFiles/www/gunicorn.logs -w 3 -b 0.0.0.0:8000


