#!/bin/bash
# a lancer sur l'hote qui heberge les conteneurs. Verifier que borgbackup soit bien installé !
# Créer une clé ssh dans le conteneur et copier la avec : ssh-copy-id tibilletbackup@de.codecommun.co -p 49422

export PGPASSWORD=$POSTGRES_PASSWORD
export PGUSER=$POSTGRES_USER
export PGHOST=cashless_postgres

DATE_NOW=$(date +%Y-%m-%d-%H-%M)
MIGRATION=$(ls /DjangoFiles/APIcashless/migrations | grep -E '^[0]' | tail -1 | head -c 4)

PREFIX=$DOMAIN-M$MIGRATION

DUMPS_DIRECTORY="/SaveDb/dumps"

echo $DATE_NOW" sql dump"
/usr/bin/pg_dumpall | gzip >$DUMPS_DIRECTORY/$PREFIX-$DATE_NOW.sql.gz

echo $DATE_NOW" delete old archive > 30min"
/usr/bin/find $DUMPS_DIRECTORY -mmin +30 -type f -delete

#### BORG SEND TO SSH ####

export BORG_REPO=$BORG_REPO
export BORG_PASSPHRASE=$BORG_PASSPHRASE
export BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes
export BORG_RELOCATED_REPO_ACCESS_IS_OK=yes

echo $DATE_NOW" borg archive creation"
/usr/bin/borg create -vs --compression lz4 \
  $BORG_REPO::$PREFIX-$DATE_NOW \
  $DUMPS_DIRECTORY

echo $DATE_NOW" prune old borg"
/usr/bin/borg prune -v --list --keep-within=3d --keep-daily=7 --keep-weekly=4 --keep-monthly=-1 --keep-yearly=-1 $BORG_REPO
