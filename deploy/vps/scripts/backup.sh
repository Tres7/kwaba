#!/usr/bin/env bash
# Backup of the database and of the private files: scripts/backup.sh [label]. Verified (pg_restore --list, gzip -t),
# kept locally, and copied to R2 when configured, encrypted with age first (both hold users' personal data; only the
# public key is on the VPS). Labels starting with avant- (before a deployment): database only.
source "$(dirname "$0")/lib.sh"

label=${1:-quotidienne}
# shellcheck source=/dev/null
if [ -f env/backup.env ]; then set -a; source env/backup.env; set +a; fi

# Dead man's switch (healthchecks.io or compatible): every run reports success or failure (/fail), and the check
# alerts on its own when a night is missing. A failed ping never changes the backup's exit status.
report_healthcheck() {
  local status=$?
  if [ -n "${BACKUP_HEALTHCHECK_URL:-}" ]; then
    local url=${BACKUP_HEALTHCHECK_URL%/}
    [ "$status" -eq 0 ] || url="${url}/fail"
    curl -fsS -m 10 --retry 3 -o /dev/null "$url" || echo "Healthcheck injoignable : ${url}" >&2
  fi
  return "$status"
}
trap report_healthcheck EXIT

mkdir -p backups && chmod 700 backups
file="backups/kwaba-$(date -u +%Y%m%dT%H%M%SZ)-${label}.dump"

log "Sauvegarde ${file}"
# Variables expanded inside the PostgreSQL container (its credentials), not on the host
# shellcheck disable=SC2016
kwaba_compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "${file}.tmp"
kwaba_compose exec -T postgres pg_restore --list < "${file}.tmp" > /dev/null
mv "${file}.tmp" "$file"
chmod 600 "$file"
log "Sauvegarde vérifiée ($(du -h "$file" | cut -f1))"

find backups -name 'kwaba-*.dump' -mtime +"${BACKUP_KEEP_DAYS:-14}" -delete

# Private files (identity documents, signed contracts, invoices, visit photos: volume prive-data, unless they are in
# the private R2 bucket). Every night and on demand, not before each deployment: migrations never touch them.
prive=""
if [[ $label != avant-* ]]; then
  prive="backups/kwaba-prive-$(date -u +%Y%m%dT%H%M%SZ)-${label}.tar.gz"
  kwaba_compose run --rm --no-deps -T --entrypoint tar api -C /app/prive -czf - . > "${prive}.tmp"
  gzip -t "${prive}.tmp"
  mv "${prive}.tmp" "$prive"
  chmod 600 "$prive"
  log "Fichiers privés sauvegardés ($(du -h "$prive" | cut -f1))"
  # Can be large: kept locally for less time than the database
  find backups -name 'kwaba-prive-*.tar.gz' -mtime +"${BACKUP_PRIVE_KEEP_DAYS:-3}" -delete
fi

# Encrypted with age, then sent to R2 under the given prefix
envoyer_r2() {
  local source=$1 prefixe=$2
  age --recipient "$BACKUP_AGE_RECIPIENT" --output "${source}.age" "$source"
  chmod 600 "${source}.age"
  docker run --rm -v "${KWABA_DIR}/backups:/backups:ro" \
    -e AWS_ACCESS_KEY_ID="$BACKUP_R2_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$BACKUP_R2_SECRET_ACCESS_KEY" \
    -e AWS_DEFAULT_REGION=auto \
    amazon/aws-cli@sha256:ce44b800602264c12298bbf3399055a4cefdb9ed4a098abe564afe26e7071bce \
    s3 cp "/backups/$(basename "$source").age" "s3://${BACKUP_R2_BUCKET}/${prefixe}/" \
    --endpoint-url "$BACKUP_R2_ENDPOINT_URL" --only-show-errors
  rm -f "${source}.age"
}

if [ -n "${BACKUP_R2_BUCKET:-}" ]; then
  if [ -z "${BACKUP_AGE_RECIPIENT:-}" ]; then
    echo "BACKUP_AGE_RECIPIENT absent : copie sur R2 refusée (jamais de sauvegarde en clair hors du VPS)" >&2
    exit 1
  fi
  envoyer_r2 "$file" postgres
  if [ -n "$prive" ]; then envoyer_r2 "$prive" prive; fi
  log "Copie chiffrée envoyée sur R2 (${BACKUP_R2_BUCKET})"
else
  log "BACKUP_R2_BUCKET absent : sauvegarde locale uniquement"
fi
