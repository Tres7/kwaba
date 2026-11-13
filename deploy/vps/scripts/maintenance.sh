#!/usr/bin/env bash
# Scheduled tasks (cron): scripts/maintenance.sh flush-tokens | renew-certs
# By hand on the preprod: scripts/maintenance.sh seed-demo
source "$(dirname "$0")/lib.sh"

case "${1:-}" in
  flush-tokens)
    # Expired JWT tokens of the blacklist (otherwise the table grows with every login)
    [ -f .deploy.env ] || { log "Pas encore déployé"; exit 0; }
    kwaba_compose run --rm --no-deps api python manage.py flushexpiredtokens
    log "Jetons expirés purgés"
    # Temporary admins who no longer sign in: those who do lose their rights at their next request
    kwaba_compose run --rm --no-deps api python manage.py retirer_admins_expires
    kwaba_compose run --rm --no-deps api python manage.py purge_activity
    log "Journal d'activité purgé (plus de 12 mois)"
    ;;
  renew-certs)
    kwaba_compose --profile tools run --rm certbot renew --webroot -w /var/www/certbot --quiet
    if [ -f .deploy.env ]; then kwaba_compose exec -T nginx nginx -s reload; fi
    log "Certificats vérifiés"
    ;;
  seed-demo)
    # Fictional listings, NGOs and accounts: both commands refuse the production domain (server/config/demo.py)
    [ -f .deploy.env ] || { log "Pas encore déployé"; exit 1; }
    kwaba_compose run --rm --no-deps api python manage.py seed_demo
    kwaba_compose run --rm --no-deps api python manage.py seed_give_demo
    log "Données de démonstration prêtes"
    ;;
  *)
    echo "usage: maintenance.sh flush-tokens | renew-certs | seed-demo" >&2
    exit 2
    ;;
esac
