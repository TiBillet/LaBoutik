#!/bin/bash
# a lancer sur l'hote qui heberge les conteneurs. Verifier que borgbackup soit bien installé !
# Créer une clé ssh dans le conteneur et copier la avec : ssh-copy-id tibilletbackup@de.codecommun.co -p 49422

export PGPASSWORD=$POSTGRES_PASSWORD
export PGUSER=$POSTGRES_USER
export PGHOST=cashless_postgres

DATE_NOW=$(date +%Y-%m-%d-%H-%M)
MIGRATION=$(ls /DjangoFiles/APIcashless/migrations | grep -E '^[0]' | tail -1 | head -c 4)

PREFIX=$PREFIX_SAVE_DB-M$MIGRATION

DUMPS_DIRECTORY="/SaveDb/dumps"

echo $DATE_NOW" on dump la db en sql "
/usr/bin/pg_dumpall | gzip >$DUMPS_DIRECTORY/$PREFIX-$DATE_NOW.sql.gz

echo $DATE_NOW" on supprime les vieux dumps sql de plus de 30min"
/usr/bin/find $DUMPS_DIRECTORY -mmin +30 -type f -delete

#### BORG SEND TO SSH ####

export BORG_REPO=$BORG_REPO
export BORG_PASSPHRASE=$BORG_PASSPHRASE
export BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes
export BORG_RELOCATED_REPO_ACCESS_IS_OK=yes

echo $DATE_NOW" on cree l'archive borg "
/usr/bin/borg create -vs --compression lz4 \
  $BORG_REPO::$PREFIX-$DATE_NOW \
  $DUMPS_DIRECTORY

/usr/bin/borg prune -v --list --keep-within=3d --keep-daily=7 --keep-weekly=4 --keep-monthly=-1 --keep-yearly=-1 $BORG_REPO
