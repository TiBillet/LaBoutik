#!/bin/bash
set -e

# -B pour beat
poetry run celery -A Cashless worker -l INFO -B