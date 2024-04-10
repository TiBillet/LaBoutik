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


# gunicorn Cashless.wsgi --log-level=debug --log-file /DjangoFiles/www/gunicorn.logs -w 3 -b 0.0.0.0:8000
sleep 2400h
