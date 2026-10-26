#!/usr/bin/env bash
# Checks that a backup really restores: restore into a throwaway PostgreSQL (Docker), never into
# the production database, then count the rows.
#
# Usage : deploy/scripts/test-restauration.sh <fichier.dump>
#   Backups produced by deploy/vps/scripts/backup.sh (pg_dump custom format, /opt/kwaba/backups).
#   PG_VERSION: major version of the restore container (16 by default, the production one); it must be
#   at least the version of the pg_dump that produced the backup.
# To run at least once a month, and after every PostgreSQL version change. A backup
# never restored is not a backup.
set -euo pipefail

fichier="${1:?chemin de la sauvegarde (.dump)}"
conteneur="kwaba-test-restauration-$$"
mot_de_passe="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')"

nettoyer() { docker rm -f "$conteneur" >/dev/null 2>&1 || true; }
trap nettoyer EXIT

docker run -d --name "$conteneur" -e POSTGRES_PASSWORD="$mot_de_passe" -e POSTGRES_DB=restauration \
  "postgres:${PG_VERSION:-16}-alpine" >/dev/null
for _ in $(seq 1 60); do
  # TCP: the temporary server of the initialisation only listens on the local socket, then restarts
  docker exec "$conteneur" pg_isready -h 127.0.0.1 -U postgres -d restauration >/dev/null 2>&1 && break
  sleep 1
done

docker exec -i "$conteneur" pg_restore -h 127.0.0.1 --no-owner --no-privileges --exit-on-error -U postgres -d restauration < "$fichier"

requete() { docker exec "$conteneur" psql -h 127.0.0.1 -U postgres -d restauration -tAc "$1"; }
utilisateurs=$(requete 'SELECT count(*) FROM users_user')
echo "Migrations appliquées : $(requete 'SELECT count(*) FROM django_migrations')"
echo "Utilisateurs          : ${utilisateurs}"
echo "Hébergements          : $(requete 'SELECT count(*) FROM hebergements_hebergementmodel')"
echo "Réservations          : $(requete 'SELECT count(*) FROM reservations_reservationmodel')"

if [ "$utilisateurs" -eq 0 ]; then
  echo "ERREUR : aucun utilisateur restauré" >&2
  exit 1
fi
echo "Restauration réussie."
