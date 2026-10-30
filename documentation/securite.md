# Sécurité

Ce que fait le code, et ce qu'il reste à régler au déploiement. Fait suite à l'audit d'octobre 2026 (50 points).

## Avant la mise en production

### Variables d'environnement de l'API

| Variable | Valeur en production | Pourquoi |
| --- | --- | --- |
| `DJANGO_DEBUG` | absente ou `False` | `True` expose les traces d'erreur et la configuration |
| `DJANGO_SECRET_KEY` | 50+ caractères aléatoires | obligatoire, le serveur refuse de démarrer sans elle |
| `POSTGRES_PASSWORD` | long et aléatoire | obligatoire hors développement (plus de mot de passe par défaut) |
| `POSTGRES_USER` | `kwaba_app` | rôle à droits minimaux, voir plus bas |
| `JWT_SIGNING_KEY` | optionnelle | à défaut, dérivée de `DJANGO_SECRET_KEY` (clé distincte pour les JWT) |
| `DJANGO_NUM_PROXIES` | `1`, fixé dans `deploy/vps/compose.yml` (nginx du VPS ajoute l'adresse réelle dans `X-Forwarded-For`) | adresse IP réelle du client pour les limites de débit et le journal d'audit |
| `FORWARDED_ALLOW_IPS` | `*` sur le VPS (l'API n'est joignable que par le réseau interne Docker) | en-têtes `X-Forwarded-*` acceptés par Gunicorn |
| `DJANGO_ADMIN_URL` | `admin/` sur le VPS : nginx ne route que `/admin/` vers Django, changer les deux ensemble | les connexions à l'administration sont de toute façon limitées et journalisées |
| `ADMINS` | `tech@kwa-ba.com` | reçoit les erreurs 500 par email |
| `FEDAPAY_WEBHOOK_SECRET` | clé du tableau de bord FedaPay | obligatoire : sans elle, les webhooks sont refusés |
| `GOOGLE_CLIENT_ID` | identifiant OAuth web de Kwa-Ba | sans lui, la connexion Google est désactivée |
| `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` | clés Cloudflare Turnstile (tableau de bord Cloudflare → Turnstile, domaine `kwa-ba.com`, mode « Managed ») | captcha à la connexion et à l'inscription ; sans elles, il est désactivé. Lues à l'exécution : pas de rebuild du frontend |
| `CORS_ALLOWED_ORIGINS` | l'URL exacte du site | jamais `*` |

### Frontend

- `AUTH_SECRET` : 32+ octets aléatoires (`openssl rand -base64 32`), différent de toutes les autres clés.
- `AUTH_URL` en `https://` : les cookies de session sont alors `Secure`.
- Les en-têtes de sécurité (CSP, HSTS, X-Frame-Options…) sont envoyés par Next.js (`client/next.config.ts`). Une nouvelle ressource externe (script, iframe, API) doit y être ajoutée à la CSP, sinon le navigateur la bloque.

### Base de données

1. La base n'est jamais accessible depuis Internet : réseau privé de l'hébergeur uniquement (pas de port public, ou liste blanche d'adresses).
2. Créer le rôle de l'application : `deploy/postgres/roles.sql`. Il lit et écrit des lignes, mais ne peut ni modifier le schéma, ni créer de rôle, ni effacer le journal d'audit.
3. Services web et workers : `POSTGRES_USER=kwaba_app`. Les migrations (`manage.py migrate`) tournent avec le rôle propriétaire.

### Stockage des photos (Cloudflare R2)

- Le bucket est public en lecture via son domaine (`R2_PUBLIC_DOMAIN`), pas en listage.
- Le jeton API R2 est limité à ce seul bucket, avec les droits « Object Read & Write », sans accès au compte.

### À ne jamais déployer

pgAdmin et la console de gestion RabbitMQ (`compose.yaml` sert au développement). En production, le broker n'est joignable que par les services, avec un utilisateur et un mot de passe dédiés (jamais `guest`).

## Sauvegardes

- Chaque nuit et avant chaque déploiement : `deploy/vps/scripts/backup.sh` (voir `deploy/vps/README.md`). Remplir `env/backup.env` pour que les sauvegardes soient copiées **hors du VPS** (R2, bucket privé).
- Chaque mois, et après chaque changement de version de PostgreSQL : `deploy/scripts/test-restauration.sh <fichier.dump>`. Le script restaure dans un PostgreSQL jetable, jamais dans la base de production, et compte les lignes. `PG_VERSION` doit être au moins égale à la version du `pg_dump` qui a produit la sauvegarde.

## Surveillance

- **Disponibilité** : un service de surveillance externe (UptimeRobot, Better Stack…) interroge `/api/health/` et la page d'accueil toutes les minutes, et alerte par email ou SMS.
- **Erreurs** : les erreurs 500 partent par email aux `ADMINS` (sans les variables locales). La sonde de santé est exclue pour ne pas envoyer un email par appel pendant une panne.
- **Paiements** : les anomalies (versement échoué, remboursement manuel) envoient déjà une alerte email (`apps/paiements/notifications.py`).
- **Journal d'audit** : administration Django → Sécurité → Journal d'audit (lecture seule). Il contient les connexions, les échecs, les blocages, les réinitialisations de mot de passe, les changements de rôle, les changements de compte de versement et les webhooks refusés. À consulter en cas de doute sur un compte, notamment après une alerte « compte de versement modifié ».

## Ce que fait le code

### Authentification

- **Connexion** : 10 essais par adresse email par quart d'heure, comptés avant la vérification du mot de passe (exact même avec des requêtes simultanées). Le temps de réponse est le même que le compte existe ou non.
- **Codes à 6 chiffres** (vérification d'email, réinitialisation) :
  - stockés sous forme d'empreinte HMAC ;
  - un code est invalidé après 5 échecs ;
  - 10 essais par heure et par adresse, nouveaux codes compris : redemander un code ne donne pas d'essais supplémentaires.
- **Limites par adresse IP** : inscription 10/h, codes 30/h, envois de codes 10/h, Google 30/min, connexion 60 par quart d'heure. Ces routes passent par le serveur Next.js, qui transmet à l'API le `X-Forwarded-For` reçu de nginx : tout nouvel appel de serveur à serveur soumis à une limite par IP doit faire de même.
- **Compteurs atomiques** : les limites reposent sur `apps/securite/limites.py` (une requête PostgreSQL `INSERT … ON CONFLICT` par incrément). Le cache de Django lit puis écrit en deux temps : il laisserait passer des requêtes simultanées.
- **Jetons** :
  - jeton d'accès valable 15 minutes ;
  - les jetons portent une empreinte du mot de passe, donc en changer invalide tous les jetons d'accès émis avant ;
  - une réinitialisation ou une désactivation met tous les refresh tokens sur liste noire ;
  - la déconnexion met le refresh token de la session sur liste noire (`POST /v1/auth/logout/`, appelé par le serveur Next.js). Le jeton d'accès reste valable jusqu'à son expiration, 15 minutes au plus. Une lecture de session encore en cours peut remettre le cookie juste après son effacement : le serveur Next.js garde la session en mémoire (`lib/sessions-fermees.ts`) et la lecture suivante la referme.
- **Session NextAuth** : l'identité et le rôle viennent toujours de l'API (`/users/me/`), jamais du navigateur.
- **Aucun jeton dans le navigateur** : les jetons de l'API restent dans le cookie de session chiffré, `HttpOnly`, et `/api/auth/session` n'en renvoie aucun.
  - La connexion par mot de passe, par Google et par code passe par le serveur Next.js (`authorize()` d'Auth.js).
  - Le navigateur appelle `/api/proxy/…`, qui ajoute le jeton puis relaie vers Django (`client/src/app/api/proxy`). Seules les routes `/v1/…` sont accessibles. Une écriture doit venir du site (contrôle d'`Origin`), car le cookie remplace le Bearer, qui protégeait du CSRF. Django reçoit l'hôte public par `X-Forwarded-Host` (`USE_X_FORWARDED_HOST`), imposé par nginx et le proxy, et toujours soumis à `ALLOWED_HOSTS`.
  - Le proxy ne fait que lire le cookie. Le renouvellement reste dans `/api/auth/session`, seul endroit qui peut enregistrer les nouveaux jetons : ne pas utiliser `auth()` dans le proxy, qui perdrait le `Set-Cookie`.
  - Une XSS ne peut plus voler de jeton, mais elle peut encore appeler le proxy tant que la page est ouverte : la CSP reste indispensable.
- **Redirection après connexion** : `safeCallback` (`client/src/lib/redirection.ts`) contrôle l'adresse telle que le navigateur la lit, résultat compris. Tout nouveau paramètre de redirection doit passer par cette fonction.
- **Administration Django** : 5 échecs par email et 20 par IP par quart d'heure, échecs journalisés.

### Données et entrées

- **Isolation entre utilisateurs** : chaque vue filtre sur l'utilisateur connecté (réservations, annonces, messagerie, voyages, dons, transferts, Concierge). Un objet d'un autre utilisateur répond 404, comme un objet inexistant.
- **Prix** : toujours recalculés côté serveur. Les webhooks FedaPay ne servent qu'à relire la transaction chez FedaPay, une seule fois (verrou).
- **Images** : les URL d'images (annonces, avatars) doivent venir d'un hôte connu (`IMAGES_HOTES_AUTORISES`). Une image externe permettrait à son auteur de collecter l'adresse IP des visiteurs. La directive `img-src` de la CSP (`client/next.config.ts`) porte la même liste : un hôte ajouté d'un côté doit l'être de l'autre.
- **Photos envoyées** : ré-encodées en JPEG, métadonnées (GPS) supprimées, nom de fichier choisi par le serveur.
- **Concierge IA** :
  - outils en lecture seule sur des données publiques ;
  - rien n'est créé sans clic du voyageur ;
  - quota atomique par utilisateur ;
  - les textes des hôtes et du web sont présentés au modèle comme des données, jamais comme des instructions.
- **Journaux** : jamais de code, de mot de passe ni de jeton. En développement seulement, le code de vérification est affiché pour tester sans SMTP.

### Points ouverts

- **Inscription** : elle indique qu'une adresse a déjà un compte (choix d'ergonomie), dans la limite de 10 essais par heure et par adresse IP.
- **Numéros Mobile Money** : ils sont stockés en clair, car ils sont nécessaires aux versements. Le chiffrement au repos dépend de l'hébergeur de la base.
- **Montées de version majeures** à planifier, chacune dans sa propre PR : Next.js 16, Tailwind 4, ESLint 10, next-auth (stable dès sa sortie).
