#!/bin/bash
set -e

# mkdir /root/.ssh
#touch /root/.ssh/known_hosts

# ssh-keyscan aaa.3peaks.re >> /root/.ssh/known_hosts

### BACKUPS FOLDER && cron
echo "Check dump backup folder"
mkdir -p /Backup/dumps
touch /Backup/backup.log
# cron n'a pas accès aux variables d'env du conteneur. On copie et on le sourcera dans le cron :
# declare plutot que printenv pour échaper les carac' spéciaux
declare -p | grep -E 'POSTGRES_PASSWORD|POSTGRES_USER|DOMAIN|BORG_REPO|BORG_PASSPHRASE' > /home/tibillet/.env_for_cron_backup
echo "Start cron task on tibillet user : "
cron
service cron status

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
