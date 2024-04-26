#!/bin/bash
set -e

# mkdir /root/.ssh
#touch /root/.ssh/known_hosts

#ssh-keyscan aaa.3peaks.re >> /root/.ssh/known_hosts

#crontab /DjangoFiles/cron/cron
#service cron start

mkdir -p /DjangoFiles/logs
touch /DjangoFiles/logs/nginxAccess.log
touch /DjangoFiles/logs/nginxError.log
touch /DjangoFiles/logs/gunicorn.logs

cd /DjangoFiles

poetry run python manage.py collectstatic --noinput

#sleep infinity
poetry run gunicorn Cashless.wsgi --log-level=info --access-logfile /DjangoFiles/logs/gunicorn.logs --log-file /DjangoFiles/logs/gunicorn.logs --error-logfile /DjangoFiles/logs/gunicorn.logs --log-level debug --capture-output --reload -w 3 -b 0.0.0.0:8000
