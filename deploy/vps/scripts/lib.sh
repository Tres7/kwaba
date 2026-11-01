# shellcheck shell=bash
# Shared helpers for the VPS scripts (to be sourced).
set -euo pipefail

KWABA_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$KWABA_DIR"

# What makes another environment different from the production (absent there): project name, compose files, domain,
# TLS mode. On the server only, like the secrets (rsync never touches env/); written by Ansible (role kwaba).
if [ -f env/deploy.conf ]; then
  # shellcheck source=/dev/null
  source env/deploy.conf
fi

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

# docker compose with the images of the last deployment (.deploy.env, or KWABA_ENV_FILE during a deployment).
# Before any deployment, placeholder values are enough for the tools (certbot, backups, etc.).
kwaba_compose() {
  local env_file=${KWABA_ENV_FILE:-.deploy.env}
  if [ -f "$env_file" ]; then
    docker compose --env-file "$env_file" "$@"
  else
    SERVER_IMAGE=non-deploye CLIENT_IMAGE=non-deploye docker compose "$@"
  fi
}

require_env_files() {
  local missing=0
  for f in env/server.env env/client.env env/postgres.env env/rabbitmq.env env/nginx.env; do
    if [ ! -s "$f" ]; then echo "Fichier manquant ou vide : $f (modèle : $f.example)" >&2; missing=1; fi
  done
  return "$missing"
}
