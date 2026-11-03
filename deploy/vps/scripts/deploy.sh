#!/usr/bin/env bash
# Deploys a manifest: scripts/deploy.sh <manifest> <server image> <client image>
# Fixed order: backup, images, migrations, server and workers, client, nginx, health check.
source "$(dirname "$0")/lib.sh"

manifest=${1:?usage: deploy.sh <manifest> <image serveur> <image client>}
server_image=${2:?image serveur manquante}
client_image=${3:?image client manquante}
domain=${KWABA_DOMAIN:-kwa-ba.com}
# nginx: HTTPS handled by nginx (production); proxy: plain HTTP behind the shared Caddy of the server (preprod)
tls_mode=${KWABA_TLS_MODE:-nginx}
# Local trials only: published HTTPS port, curl options (self-signed certificate), images already present
https_port=${HTTPS_PORT:-443}
read -r -a health_curl_opts <<< "${KWABA_HEALTH_CURL_OPTS:-}"

require_env_files
case "$tls_mode" in
  nginx)
    if ! kwaba_compose --profile tools run --rm --entrypoint test certbot -s "/etc/letsencrypt/live/${domain}/fullchain.pem"; then
      echo "Pas de certificat pour ${domain} : lancer d'abord scripts/init-tls.sh" >&2
      exit 1
    fi
    ;;
  proxy)
    # Caddy holds the certificate; nginx must reach it through the shared network
    docker network inspect proxy > /dev/null || { echo "Réseau Docker « proxy » absent : Caddy partagé non installé (Ansible, rôle proxy)" >&2; exit 1; }
    ;;
  *)
    echo "KWABA_TLS_MODE inconnu : ${tls_mode} (nginx ou proxy)" >&2
    exit 1
    ;;
esac

export KWABA_ENV_FILE=.deploy.env.next
printf 'SERVER_IMAGE=%s\nCLIENT_IMAGE=%s\nMANIFEST=%s\n' "$server_image" "$client_image" "$manifest" > "$KWABA_ENV_FILE"

log "Déploiement de ${manifest}"
log "Images"
if [ "${KWABA_SKIP_PULL:-0}" != "1" ]; then kwaba_compose pull api client; fi

log "Base et broker"
annexes=()
# Preprod only (compose.preprod.yml): Mailpit catches every email
if kwaba_compose config --services | grep -qx mailpit; then annexes+=(mailpit); fi
kwaba_compose up -d --wait postgres rabbitmq "${annexes[@]}"

log "Sauvegarde de la base avant migrations"
scripts/backup.sh "avant-${manifest%.yaml}"

log "Migrations"
kwaba_compose run --rm --no-deps api python manage.py migrate --noinput

# Private files written before the prive-data volume existed are still in the running containers, which are about to be
# replaced: they are copied into the volume first (a file already there is never overwritten).
for service in api consumer relay payments; do
  conteneur=$(kwaba_compose ps -q "$service")
  [ -n "$conteneur" ] || continue
  montages=$(docker inspect -f '{{range .Mounts}}{{println .Destination}}{{end}}' "$conteneur")
  if ! grep -qx /app/prive <<< "$montages"; then
    log "Fichiers privés de ${service} copiés dans le volume prive-data"
    kwaba_compose exec -T "$service" tar -C /app/prive -cf - . \
      | kwaba_compose run --rm --no-deps -T --entrypoint tar api -C /app/prive -xf - --skip-old-files
  fi
done

log "Serveur et workers"
kwaba_compose up -d --wait api consumer relay payments

log "Client"
kwaba_compose up -d --wait client

log "nginx (configuration vérifiée, puis conteneur recréé : templates et adresses de l'API et du client à jour)"
# The template is rendered and tested in a throwaway container before replacing the running nginx
kwaba_compose run --rm --no-deps nginx nginx -t
kwaba_compose up -d --force-recreate nginx

log "Test de santé"
check() {
  if [ "$tls_mode" = proxy ]; then
    # No published port: from inside the nginx container, as the shared Caddy sends it (HTTP, public host, https)
    kwaba_compose exec -T nginx curl -fsS --retry 10 --retry-delay 3 --retry-all-errors \
      -H "Host: ${domain}" -H "X-Forwarded-Proto: https" -o /dev/null -w "%{http_code} $1\n" "http://127.0.0.1$1"
  else
    curl -fsS --retry 10 --retry-delay 3 --retry-all-errors "${health_curl_opts[@]}" \
      --resolve "${domain}:${https_port}:127.0.0.1" -o /dev/null -w "%{http_code} $1\n" "https://${domain}:${https_port}$1"
  fi
}
check /api/health/
check /

[ -f .deploy.env ] && cp .deploy.env .deploy.env.previous
mv "$KWABA_ENV_FILE" .deploy.env
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) ${manifest} ${server_image} ${client_image}" >> deployments.log
log "Déployé : ${manifest}"
