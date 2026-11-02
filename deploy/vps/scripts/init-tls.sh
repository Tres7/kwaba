#!/usr/bin/env bash
# First Let's Encrypt certificate (once, with the DNS of the domain already pointing to the VPS; KWABA_DOMAIN, kwa-ba.com
# by default):
# scripts/init-tls.sh <Let's Encrypt contact email>
source "$(dirname "$0")/lib.sh"

email=${1:?usage: init-tls.sh <email>}
domain=${KWABA_DOMAIN:-kwa-ba.com}

log "nginx temporaire (HTTP seul) pour le défi Let's Encrypt"
kwaba_compose --profile tools up -d acme
trap 'kwaba_compose --profile tools rm -sf acme > /dev/null' EXIT

kwaba_compose --profile tools run --rm certbot certonly --webroot -w /var/www/certbot \
  -d "$domain" -d "www.${domain}" --email "$email" --agree-tos --no-eff-email --non-interactive
log "Certificat obtenu pour ${domain} : le workflow deploy peut maintenant démarrer la production"
