# Production Kwa-Ba sur le VPS

Tout tourne sur un seul VPS (Ubuntu 24.04), en Docker Compose, dans `/opt/kwaba` :

| Service | Rôle | Exposé |
| --- | --- | --- |
| `nginx` | HTTPS (Let's Encrypt), redirections, routage : `/api/auth/*` → client, `/api/*` `/admin/*` `/static/*` → API, `/photos/*` → bucket R2 (avec cache), le reste → client | 80, 443 |
| `client` | Site Next.js (image `kwaba-client`, par digest) | non |
| `api` | API Django / Gunicorn (image `kwaba-server`, par digest) | non |
| `consumer`, `relay`, `payments` | Emails (RabbitMQ), relais de la messagerie, worker des paiements (même image que l'API) | non |
| `postgres`, `rabbitmq` | Base et broker, volumes persistants, sur un réseau interne sans accès à Internet | non |

Les photos sont stockées sur Cloudflare R2 et servies par nginx sous `https://kwa-ba.com/photos/` : nginx les récupère à l'adresse publique `r2.dev` du bucket et les garde en cache (30 jours). Les URL enregistrées dans les annonces ne dépendent donc pas de l'hébergement des fichiers. La configuration nginx est un template (`nginx/templates/`), complété au démarrage avec `R2_PUBLIC_ORIGIN` (`env/nginx.env`) et le domaine `KWABA_DOMAIN`. Ce dernier vaut `kwa-ba.com` s'il n'est défini nulle part (la prod) ; il est aussi lu par `deploy.sh` et `init-tls.sh`, pour qu'un autre environnement (la préprod) serve son propre domaine sans toucher au code.

Les images GHCR sont publiques (dépôt public) : aucune authentification sur le VPS.

## Préparation initiale (une seule fois)

1. **DNS** (chez Hostinger, qui gère `kwa-ba.com`) : A `@` → IP du VPS, CNAME `www` → `kwa-ba.com`. Ne jamais toucher aux enregistrements de l'email (MX, SPF, DKIM).
2. **Pare-feu IONOS** (*Stratégies de pare-feu* du VPS) : entrées autorisées uniquement TCP 22, 80 et 443.
3. **Clé SSH personnelle** : sur ton poste, `ssh-keygen -t ed25519` (avec une phrase de passe), puis `ssh-copy-id root@<ip>` (mot de passe root d'IONOS, une dernière fois).
4. **Durcissement et Docker** (interactif : le script demande le mot de passe `sudo` de ton compte admin) :
   ```bash
   scp deploy/vps/scripts/setup-server.sh root@<ip>:/root/
   ssh -t root@<ip> bash /root/setup-server.sh <ton-utilisateur>
   ```
   Il crée ton compte admin (`sudo`, ta clé SSH) et l'utilisateur `deploy`, réservé à la CI (groupe `docker`, sans `sudo`, sans clé pour l'instant), puis interdit root et les mots de passe. **Ne ferme pas cette session** avant d'avoir vérifié, dans un autre terminal : `ssh <ton-utilisateur>@<ip>` puis `sudo whoami` (réponse : `root`).
5. **Clé de la CI** pour `deploy` : sur ton poste, `ssh-keygen -t ed25519 -f kwaba-deploy -N "" -C github-deploy`. La partie publique va sur le VPS :
   ```bash
   ssh <ton-utilisateur>@<ip> "sudo tee -a /home/deploy/.ssh/authorized_keys" < kwaba-deploy.pub
   ```
   La partie privée et l'empreinte du serveur (`ssh-keyscan -t ed25519 <ip>`, à comparer une fois avec `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` sur le serveur) vont dans l'environnement GitHub `production` (voir *Déployer*). Supprime ensuite la clé privée de ton poste.
6. **Fichiers** : copier `deploy/vps/` dans `/opt/kwaba` (le workflow `deploy` le refait ensuite à chaque déploiement). Les étapes manuelles passent par ton compte admin, `deploy` n'ayant que la clé de la CI :
   ```bash
   rsync -a --exclude 'env/*.env' deploy/vps/ <ton-utilisateur>@<ip>:/tmp/kwaba/
   ssh -t <ton-utilisateur>@<ip> 'sudo rsync -a /tmp/kwaba/ /opt/kwaba/ && sudo chown -R deploy:deploy /opt/kwaba && sudo chmod 700 /opt/kwaba/env && rm -rf /tmp/kwaba'
   ```
7. **Secrets** : sur le VPS, dans `/opt/kwaba/env/`, créer `server.env`, `client.env`, `postgres.env`, `rabbitmq.env`, `nginx.env` et `backup.env` à partir des modèles `*.env.example` (par exemple `sudo -u deploy cp env/server.env.example env/server.env` puis `sudo -u deploy nano env/server.env`), puis `sudo -u deploy chmod 600 env/*.env`. Ils ne quittent jamais le serveur.
   - **R2 (photos)** : créer un bucket, activer son accès public par l'adresse `r2.dev` (*Settings → Public access*), mettre cette adresse dans `nginx.env` (`R2_PUBLIC_ORIGIN`), et une clé d'API limitée à ce bucket dans `server.env` (`R2_*`). `R2_PUBLIC_DOMAIN` reste `kwa-ba.com/photos`.
   - **R2 (sauvegardes)** : un second bucket, privé, de juridiction UE (choix proposé à la création du bucket), avec sa propre clé limitée à ce bucket (`backup.env`).
   - **Chiffrement des sauvegardes** : sur ton poste, `age-keygen -o kwaba-backups.key`. Garde ce fichier dans un gestionnaire de mots de passe (sans lui, les sauvegardes sur R2 sont illisibles) et mets seulement la clé publique (`age1…`) dans `backup.env`.
8. **Certificat** : une fois le DNS propagé (`dig +short kwa-ba.com` renvoie l'IP du VPS) :
   ```bash
   ssh -t <ton-utilisateur>@<ip> sudo -u deploy /opt/kwaba/scripts/init-tls.sh info@kwa-ba.com
   ```
9. **Premier déploiement** : workflow `deploy` (voir ci-dessous).
10. **Vérifications depuis l'extérieur** : `nmap -Pn <ip>` ne montre que 22, 80 et 443 ; `ssh -o PubkeyAuthentication=no <ton-utilisateur>@<ip>` est refusé ; [SSL Labs](https://www.ssllabs.com/ssltest/) sur `kwa-ba.com` ; sur le serveur, `sudo ss -tulpn` (seuls sshd et docker-proxy sur 80 et 443 écoutent publiquement).

**Entretien** : les mises à jour de sécurité d'Ubuntu s'installent seules (redémarrage automatique à 04:30 UTC si nécessaire). Docker vient d'un dépôt séparé : `sudo apt update && sudo apt upgrade` une fois par mois.

## Déployer

Workflow GitHub **deploy** (*Actions → Deploy → Run workflow*, sur `main`) : environnement `preprod` (par défaut) ou `production`, champ *manifest* vide pour le dernier, ou un nom de fichier de `deploy/manifests/`. Un seul déploiement à la fois par environnement, jamais annulé en cours.

**Parcours attendu** : un manifest va d'abord en préprod, on teste, puis **le même manifest** va en prod (même image serveur, client construit depuis la même révision). La prod refuse un manifest qui n'a pas été déployé avec succès en préprod (artefact `preprod-<manifest>` du run, gardé 90 jours) ; pour un retour arrière ou une urgence, cocher `skip_preprod` (signalé dans le résumé du run).

Le workflow :

1. vérifie le manifest (nom exact, images par digest) et prend l'image client de l'environnement (`client` ou `clientPreprod`) ;
2. se connecte en SSH (empreinte du serveur imposée, jamais acceptée à la volée) ;
3. deux modes, selon la variable `DEPLOY_PULL` de l'environnement :
   - **le serveur tire** (`true`, la préprod) : la clé ne peut lancer que la porte de déploiement du serveur (`/usr/local/bin/<nom>-deploy`, installée par Ansible, propriété de root), avec pour seul argument le nom du manifest. Le serveur récupère lui-même `main` depuis GitHub, vérifie que le manifest y est, lit les images dedans, met à jour la configuration (`deploy/vps`) et lance `scripts/deploy.sh`. Une clé volée ne peut donc que redéployer un manifest de `main`, ni shell, ni copie de fichiers, ni tunnel ;
   - **le workflow pousse** (la prod pour l'instant) : copie `deploy/vps/` de `main` dans `/opt/kwaba` (`rsync --delete`, sans jamais toucher à `env/`, `backups/`, `logs/`, `.deploy.env*`, `deployments.log`), puis lance `scripts/deploy.sh` ;
4. vérifie `/api/health/` et `/` depuis Internet (en préprod, `/` doit répondre 401 : le mot de passe est bien demandé).

Environnements GitHub (*Settings → Environments*), branche `main` seulement :

| | `production` | `preprod` |
| --- | --- | --- |
| Secrets | `DEPLOY_SSH_KEY`, `DEPLOY_SSH_KNOWN_HOSTS` | les mêmes, avec la clé `kwaba-preprod-deploy` et `[217.154.19.172]:2222 ssh-ed25519 …` |
| `DEPLOY_HOST` | IP du VPS | `217.154.19.172` |
| `DEPLOY_PORT` | (22) | `2222` |
| `DEPLOY_USER` | (`deploy`) | `deploy-kwaba` |
| `DEPLOY_PATH` | (`/opt/kwaba`) | inutile (le serveur tire) |
| `DEPLOY_PULL` | (vide) | `true` |
| `DEPLOY_SITE_URL` | (variable du dépôt `PUBLIC_SITE_URL`) | `https://preprod.kwa-ba.com` |

Entre parenthèses : la valeur par défaut, rien à créer.

Sur le VPS, le workflow appelle :

```bash
scripts/deploy.sh <manifest> <image serveur> <image client>
```

Ordre fixe : sauvegarde de la base (vérifiée), images, migrations, serveur et workers, client, nginx (configuration testée dans un conteneur jetable, puis conteneur recréé), test de santé (`/api/health/` et `/`). Si la configuration nginx est invalide, le déploiement s'arrête avant de toucher au nginx en service. L'état déployé est dans `.deploy.env` (le précédent dans `.deploy.env.previous`), l'historique dans `deployments.log`.

## Revenir en arrière

Relancer le workflow **deploy** avec un manifest antérieur (en prod, cocher `skip_preprod` s'il n'est jamais passé par la préprod ; un manifest antérieur à la préprod, sans `clientPreprod`, ne se déploie qu'en prod) (les images changent ; la configuration `deploy/vps` reste celle de `main`). Les migrations ne sont pas annulées : elles doivent rester rétro-compatibles (ajouter avant de supprimer), ce qui permet à l'ancien code de tourner sur le nouveau schéma.

## Sauvegardes et restauration

- Automatiques : chaque nuit (03:30 UTC) et avant chaque déploiement, dans `/opt/kwaba/backups` (14 jours). Si `env/backup.env` est rempli, une copie **chiffrée avec age** part sur R2 (aucune copie en clair ne quitte le VPS).
- **Surveillance** : sur [healthchecks.io](https://healthchecks.io) (gratuit), créer un check *Period* 1 jour, *Grace* 2 heures, avec une alerte par email vers vous deux. Mettre son adresse de ping dans `BACKUP_HEALTHCHECK_URL` (`env/backup.env`). Chaque sauvegarde la signale (`/fail` en cas d'erreur) ; une nuit sans sauvegarde déclenche aussi l'alerte. Vérifier une fois avec `sudo -u deploy /opt/kwaba/scripts/backup.sh manuelle` : le check passe au vert.
- **Copies sur R2 protégées et purgées** (tableau de bord Cloudflare → R2 → `kwaba-backups` → *Settings*) :
  - *Bucket lock rules* → règle sur le préfixe `postgres/`, rétention **30 jours** : pendant 30 jours, une copie ne peut être ni effacée ni écrasée, même avec la clé du VPS (un attaquant qui prend le serveur ne peut pas détruire aussi les sauvegardes) ;
  - *Object lifecycle rules* → règle sur le préfixe `postgres/`, suppression après **90 jours** (sinon les copies s'accumulent sans fin).
- Récupérer une copie de R2 : la télécharger, puis `age --decrypt --identity kwaba-backups.key -o kwaba.dump <fichier>.dump.age`.
- Restaurer (après avoir arrêté l'API et les workers) :
  ```bash
  cd /opt/kwaba
  docker compose --env-file .deploy.env stop api consumer relay payments
  docker compose --env-file .deploy.env exec -T postgres sh -c 'dropdb -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
  docker compose --env-file .deploy.env exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' < backups/<fichier>.dump
  docker compose --env-file .deploy.env up -d --wait api consumer relay payments
  ```

## Tâches planifiées (`/etc/cron.d/kwaba`)

| Heure (UTC) | Tâche |
| --- | --- |
| 03:30 | `scripts/backup.sh` |
| 04:00 | `scripts/maintenance.sh flush-tokens` (jetons JWT expirés) |
| 02:17 et 14:17 | `scripts/maintenance.sh renew-certs` |

Journaux dans `/opt/kwaba/logs/` (rotation hebdomadaire).

## Préprod (derrière le Caddy partagé du VPS personnel)

La préprod utilise les mêmes images, le même `compose.yml` et le même `deploy.sh` que la prod. Ce qui la distingue vit sur son serveur, dans `env/deploy.conf` (généré par Ansible, rôle `kwaba`, jamais touché par le rsync) :

```bash
export COMPOSE_PROJECT_NAME=kwaba-preprod
export COMPOSE_FILE=compose.yml:compose.preprod.yml
export KWABA_DOMAIN=preprod.kwa-ba.com
export KWABA_TLS_MODE=proxy
```

- **`KWABA_TLS_MODE=proxy`** : nginx sert le site en HTTP seulement (`nginx/templates/kwa-ba-proxy.inc.template`) ; le Caddy partagé du serveur fait le HTTPS et transmet `X-Forwarded-Proto: https`, repris tel quel vers Django et Auth.js. En prod (`nginx`, la valeur par défaut), nginx fait le HTTPS (`kwa-ba-nginx.inc.template`). Les deux modes partagent le corps du site (`kwa-ba-site.inc.template`).
- **`compose.preprod.yml`** : nginx sans port publié, joint par Caddy sur le réseau Docker `proxy` (conteneur `kwaba-preprod-nginx`) ; `DJANGO_NUM_PROXIES=2` (Caddy puis nginx) ; Mailpit attrape tous les emails (interface : `ssh -L 8025:localhost:8025 <hôte>`, puis `http://localhost:8025`).
- **Secrets** (`env/*.env`) : générés par Ansible depuis le Vault de `kwa-ba-infra` (voir `deploy/ansible/README.md`), jamais écrits à la main ; emails envoyés à Mailpit (`EMAIL_HOST=mailpit`, port 1025).
- **Accès** : le Caddy partagé demande un mot de passe au navigateur sur tout le site sauf le webhook FedaPay, et le garde hors des moteurs de recherche (`X-Robots-Tag: noindex`).
- **`deploy.sh`** : pas de contrôle du certificat (c'est celui de Caddy) mais vérification que le réseau `proxy` existe ; test de santé depuis le conteneur nginx.

## Essai local de la pile de production

Toute la chaîne se teste sur un poste avec Docker, sans VPS : images construites localement, secrets de test, certificat auto-signé, ports décalés.

```bash
export COMPOSE_PROJECT_NAME=kwabatest HTTP_PORT=18080 HTTPS_PORT=18443
KWABA_SKIP_PULL=1 KWABA_HEALTH_CURL_OPTS=-k scripts/deploy.sh essai kwaba-server:prod kwaba-client:prod
```

En développement (`compose.yaml` à la racine), RabbitMQ est en version 4 : si un ancien volume RabbitMQ 3 l'empêche de démarrer, supprimer ce volume de développement (`docker volume rm kwaba_rabbitmq_data`).
