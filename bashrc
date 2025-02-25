# ~/.bashrc: executed by bash(1) for non-login shells.

alias reorder="manage reorder APIcashless.categorie && manage reorder APIcashless.Articles && manage reorder APIcashless.PointDeVente && manage reorder APIcashless.Categorie && manage reorder APIcashless.Table"

alias mm="poetry run python /DjangoFiles/manage.py migrate"

alias rsp="poetry run python /DjangoFiles/manage.py runserver 0.0.0.0:8000"
alias sp="poetry run python /DjangoFiles/manage.py shell_plus"
alias cel="poetry run celery -A Cashless worker -l INFO"

alias test="poetry run python /DjangoFiles/manage.py test"

alias rcel="poetry run celery -A Cashless worker -l INFO"
alias guni="poetry run gunicorn Cashless.wsgi --capture-output --reload -w 3 -b 0.0.0.0:8000"

alias mmes="poetry run django-admin makemessages -l en && django-admin makemessages -l fr"
alias cmes="poetry run django-admin compilemessages"

alias notebook="poetry run python /DjangoFiles/manage.py shell_plus --notebook"

load_sql() {
export PGPASSWORD=$POSTGRES_PASSWORD
export PGUSER=$POSTGRES_USER
export PGHOST=postgres

psql --dbname $POSTGRES_DB -f $1

echo "SQL file loaded : $1"
}

