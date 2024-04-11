# /bin/bash
set -e
if [ "$DEBUG" == "0" ]
then
    poetry run python /home/tibillet/LaBoutik/DjangoFiles/manage.py migrate
    poetry run python /home/tibillet/LaBoutik/DjangoFiles/manage.py popdb
else
    echo "DEBUG environment variable is set : NO INSTALL"
fi
