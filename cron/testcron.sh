#!/bin/bash
set -e

whoami
DATE_NOW=$(date +%Y-%m-%d-%H-%M)
echo $DATE_NOW" START testcron script"
/bin/echo "$(date +%Y-%m-%d-%H-%M) prout" >> /Backup/backup.log
echo $DATE_NOW" END testcron script"

# pour test dans le conteneur :
# cat /etc/cron.d/cron_task
# cron && tail -f /Backup/backup.log