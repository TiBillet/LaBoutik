#!/bin/bash
set -e

# mkdir /root/.ssh
# touch /root/.ssh/known_hosts
# ssh-keyscan aaa.3peaks.re >> /root/.ssh/known_hosts

#crontab /DjangoFiles/cron/cron
#service cron start

mkdir -p /DjangoFiles/www
touch /DjangoFiles/www/nginxAccess.log
touch /DjangoFiles/www/nginxError.log

cd /DjangoFiles

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py popdb --test

python manage.py runserver 0.0.0.0:8000
#gunicorn Cashless.wsgi --log-level=debug --log-file /DjangoFiles/www/gunicorn.logs -w 3 -b 0.0.0.0:8000


