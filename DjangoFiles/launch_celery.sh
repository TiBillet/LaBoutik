#!/bin/bash
set -e

#sleep infinity
poetry run celery -A Cashless worker -l INFO

