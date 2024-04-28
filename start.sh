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
poetry run python manage.py migrate
poetry run python manage.py install

#sleep infinity

echo "Run GUNICORN"
echo "You should be able to see your instance at :"
echo "https://$DOMAIN/"

poetry run gunicorn Cashless.wsgi --log-level=info --access-logfile /DjangoFiles/logs/gunicorn.logs --log-file /DjangoFiles/logs/gunicorn.logs --error-logfile /DjangoFiles/logs/gunicorn.logs --log-level debug --capture-output --reload -w 3 -b 0.0.0.0:8000
