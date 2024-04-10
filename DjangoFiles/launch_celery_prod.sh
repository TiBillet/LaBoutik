#!/bin/bash
set -e

#sleep infinity
celery -A Cashless worker -l INFO

