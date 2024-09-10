#!/bin/bash
set -e

# mkdir /root/.ssh
#touch /root/.ssh/known_hosts

# ssh-keyscan aaa.3peaks.re >> /root/.ssh/known_hosts

### BACKUPS FOLDER && cron
echo "Check dump backup folder"
mkdir -p /Backup/dumps
touch /Backup/backup.log
echo "Start cron task on tibillet user"
cron

### LOGS
echo "Check logs files"
mkdir -p /DjangoFiles/logs
touch /DjangoFiles/logs/nginxAccess.log
touch /DjangoFiles/logs/nginxError.log
touch /DjangoFiles/logs/gunicorn.logs

## UPDATE and INSTALL if needed
echo "Django MIGRATE and INSTALL if needed"
cd /DjangoFiles
poetry run python manage.py collectstatic --noinput
poetry run python manage.py migrate
poetry run python manage.py install

echo "Run GUNICORN"
echo "You should be able to see your instance at :"
echo "https://$DOMAIN/"

poetry run gunicorn Cashless.wsgi --log-level=info --access-logfile /DjangoFiles/logs/gunicorn.logs --log-file /DjangoFiles/logs/gunicorn.logs --error-logfile /DjangoFiles/logs/gunicorn.logs --log-level debug --capture-output --reload -w 3 -b 0.0.0.0:8000
