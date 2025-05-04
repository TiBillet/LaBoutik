#!/bin/bash

### LOGS
echo "Check logs files"
# Ensure log directories exist
mkdir -p /DjangoFiles/logs/supervisor
touch /DjangoFiles/logs/gunicorn.log
touch /DjangoFiles/logs/daphne.log
touch /DjangoFiles/logs/celery.log
touch /DjangoFiles/logs/supervisor/supervisord.log
touch /DjangoFiles/logs/nginxAccess.log
touch /DjangoFiles/logs/nginxError.log
touch /DjangoFiles/logs/gunicorn.logs

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

## UPDATE and INSTALL if needed
echo "Django MIGRATE and INSTALL if needed"
cd /DjangoFiles
poetry run python manage.py collectstatic --noinput
poetry run python manage.py migrate
poetry run python manage.py install



# Start supervisor in the background
/usr/bin/supervisord -c /DjangoFiles/supervisor/supervisord.conf &

# Wait a moment for supervisor to start and create log files
sleep 2

# Tail all service logs simultaneously
echo "Tailing all service logs. Press Ctrl+C to stop viewing logs (services will continue running)."
exec tail -f /DjangoFiles/logs/gunicorn.log /DjangoFiles/logs/daphne.log /DjangoFiles/logs/celery.log /DjangoFiles/logs/supervisor/supervisord.log


# =====================================================================
# SUPERVISOR MANAGEMENT GUIDE
# =====================================================================
#
# This script starts Supervisor, which manages the following services:
# - Gunicorn: HTTP server (port 8000)
# - Daphne: WebSocket server (port 8001)
# - Celery: Background task processor
#
# =====================================================================
# VIEWING LOGS
# =====================================================================
#
# Each service logs to its own file in /DjangoFiles/logs/:
# - Gunicorn: /DjangoFiles/logs/gunicorn.log
# - Daphne: /DjangoFiles/logs/daphne.log
# - Celery: /DjangoFiles/logs/celery.log
#
# Supervisor itself logs to:
# - /DjangoFiles/logs/supervisor/supervisord.log
#
# To view logs in real-time:
# $ tail -f /DjangoFiles/logs/gunicorn.log
# $ tail -f /DjangoFiles/logs/daphne.log
# $ tail -f /DjangoFiles/logs/celery.log
#
# =====================================================================
# SUPERVISOR COMMANDS
# =====================================================================
#
# Check status of all services:
# $ supervisorctl status
#
# Check status of a specific service:
# $ supervisorctl status gunicorn
# $ supervisorctl status daphne
# $ supervisorctl status celery
#
# Start/stop/restart a service:
# $ supervisorctl start gunicorn
# $ supervisorctl stop daphne
# $ supervisorctl restart celery
#
# Start/stop/restart all services:
# $ supervisorctl start all
# $ supervisorctl stop all
# $ supervisorctl restart all
#
# Reload supervisor configuration after changes:
# $ supervisorctl reread
# $ supervisorctl update
#
# =====================================================================
# TROUBLESHOOTING
# =====================================================================
#
# If a service is not starting properly:
# 1. Check its log file for errors
# 2. Try restarting it: supervisorctl restart [service_name]
# 3. Check supervisor log: tail -f /DjangoFiles/logs/supervisor/supervisord.log
#
# If supervisor itself is not starting:
# 1. Check if the process is running: ps aux | grep supervisord
# 2. Check the supervisor log file
# 3. Ensure the configuration files are valid
#
# =====================================================================
