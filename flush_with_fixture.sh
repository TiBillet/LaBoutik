#!/bin/bash
set -e

if [ "$TEST" = "1" ]
then
    echo "Starting TiBillet/LaBoutik installation with fixtures (TEST mode)"
    poetry run ./manage.py flush --no-input
    poetry run ./manage.py migrate
    poetry run ./manage.py install_with_fixture --tdd
    poetry run ./manage.py collectstatic --no-input
    poetry run ./manage.py runserver 0.0.0.0:8000
else
    echo "Starting TiBillet/LaBoutik installation with fixtures (PRODUCTION mode)"
    echo "This will reset your database. Are you sure? (y/n)"
    read answer
    if [ "$answer" = "y" ]; then
        poetry run ./manage.py flush --no-input
        poetry run ./manage.py migrate
        poetry run ./manage.py install_with_fixture
        poetry run ./manage.py collectstatic --no-input
        echo "Installation completed. You can now start the server with:"
        echo "poetry run ./manage.py runserver 0.0.0.0:8000"
    else
        echo "Installation aborted."
    fi
fi