# /bin/bash
set -e

if [ "$TEST" = "1" ]
then
    poetry run python manage.py migrate
    poetry run python manage.py flush --no-input
    poetry run python manage.py collectstatic --no-input
    poetry run python manage.py install --tdd
    poetry run python manage.py runserver 0.0.0.0:8000
else
    echo "TEST environment variable is not set"
fi
