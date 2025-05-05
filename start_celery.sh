#!/bin/bash
set -e


echo "Starting Celery beat..."
poetry run celery -A Cashless beat -l INFO &

# Run Celery worker and beat as separate processes
echo "Starting Celery worker..."
poetry run celery -A Cashless worker -l INFO
