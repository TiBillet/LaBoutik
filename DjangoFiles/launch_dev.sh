#!/bin/bash
set -e
mkdir -p /DjangoFiles/www
touch /DjangoFiles/www/nginxAccess.log
touch /DjangoFiles/www/nginxError.log
cd /DjangoFiles

load_sql() {
  export PGPASSWORD=$POSTGRES_PASSWORD
  export PGUSER=$POSTGRES_USER
  export PGHOST=cashless_postgres
  export LOAD_SQL=$LOAD_SQL
  DB_NAME=$POSTGRES_DB
  if psql -lqtA | cut -d\| -f1 | grep -qxF "$DB_NAME"; then
    echo "La base de données ${DB_NAME} existe déjà"
  else
    echo "La base de données ${DB_NAME} n'existe pas"
    sleep 3
    psql --dbname $POSTGRES_DB -f $LOAD_SQL
    echo "SQL file loaded : $LOAD_SQL"
  fi
}

migrate() {
  python manage.py collectstatic --noinput
  python manage.py migrate
}

while getopts ":lf" option; do
  case $option in
  l) # loadsql
    load_sql
    exit
    ;;
  f) # flush
    python manage.py migrate
    python manage.py flush --no-input
    python manage.py popdb --test
    exit
    ;;
  s) # start
    python manage.py runserver 0.0.0.0:8000
    exit
    ;;
  \?) # Invalid option
    echo "Error: Invalid option"
    exit
    ;;
  esac
done

# Fonction qui sera exécutée en cas d'erreur
handle_error() {
  echo "Une erreur s'est produite dans la ligne $1"
  sleep infinity
}

trap 'handle_error $LINENO' ERR
#echo "Lancement Gunicorn"
#gunicorn Cashless.wsgi --log-level=debug --log-file /DjangoFiles/www/gunicorn.logs -w 3 -b 0.0.0.0:8000
sleep infinity
