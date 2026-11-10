#!/usr/bin/env bash
# Fingerprint of the environment the containers read (env/*.env through docker compose, and env/backup.env read by
# backup.sh): two short hashes, no value printed. Same hashes before and after rewriting the files (Ansible) = same values.
source "$(dirname "$0")/lib.sh"

conteneurs=$(kwaba_compose config --format json | python3 -c '
import hashlib, json, sys
services = json.load(sys.stdin)["services"]
environnement = {nom: service.get("environment", {}) for nom, service in services.items()}
print(hashlib.sha256(json.dumps(environnement, sort_keys=True).encode()).hexdigest()[:16],
      sum(len(valeurs) for valeurs in environnement.values()))')
sauvegardes="absent"
if [ -f env/backup.env ]; then
  sauvegardes=$(env -i bash -c 'set -a; source env/backup.env; env' | grep '^BACKUP_' | sort | sha256sum | cut -c1-16)
fi
echo "conteneurs : ${conteneurs% *} (${conteneurs#* } valeurs)"
echo "backup.env : ${sauvegardes}"
