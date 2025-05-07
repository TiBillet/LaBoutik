#! /bin/bash
set -e

if [ "$TEST" = "1" ]
then
    poetry run ./manage.py flush --no-input
    poetry run ./manage.py migrate
    poetry run ./manage.py install --tdd
    poetry run ./manage.py collectstatic --no-input
    # poetry run ./manage.py runserver 0.0.0.0:8000
    ./start_services.sh
else
    echo "TEST environment variable is not set"
fi
