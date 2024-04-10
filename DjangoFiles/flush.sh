# /bin/bash
set -e

if [ "$TEST" = "1" ]
then
    python manage.py migrate
    python manage.py flush --no-input
    python manage.py popdb --test
    python manage.py runserver 0.0.0.0:8000
else
    echo "TEST environment variable is not set"
fi
