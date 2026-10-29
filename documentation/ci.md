# CI

Chaque push sur une branche de travail lance un contrôle rapide (`push_branch.yml`) : les mêmes vérifications que le hook pre-push local. Les pull requests vers `main` lancent la chaîne complète (`pr_main.yml`).

## Sur chaque push de branche

`push_branch.yml`, sur toute branche sauf `main` et `dependabot/**` : `ruff check`, `lint-imports` et tests unitaires du serveur, ESLint et `tsc` du client, gitleaks sur les commits poussés.

## Sur chaque pull request

| Job | Contenu | Quand |
| --- | --- | --- |
| Plan | Chemins modifiés → serveur, client, infra, broker, docs seules | Toujours |
| App / Serveur | `ruff check`, `lint-imports`, `makemigrations --check`, `check --deploy` (bloquant sur tout avertissement), tests `unit` puis `integration` (PostgreSQL 16), couverture combinée et ses deux seuils (voir plus bas) | `server/**` ou `.github/**` modifié |
| App / Client | ESLint, `tsc` | `client/**` ou `.github/**` modifié |
| Config | actionlint (workflows, avec shellcheck), hadolint (Dockerfiles) | Workflows, Dockerfiles ou compose modifiés |
| Docker | `docker compose config` ; image du serveur : build, smoke test (non root, migrations, `/api/health/` contre un PostgreSQL jetable), Trivy ; image du client : build Next.js, smoke test (non root, pages et Auth.js derrière un proxy simulé), Trivy | Après App et Config, hors brouillon |
| Security | gitleaks sur les commits de la PR ; `npm audit --omit=dev --audit-level=high` (client) et `pip-audit` (serveur) selon la partie modifiée | Toujours, en parallèle |
| PR status | Échoue si un job a échoué ou été annulé ; un job ignoré est toléré | Toujours |

Trivy échoue sur toute vulnérabilité HIGH ou CRITICAL **qui a un correctif disponible**, et sur tout secret HIGH ou CRITICAL embarqué dans l'image ; le rapport complet est dans le résumé du job.

gitleaks masque les valeurs dans les logs. Un faux positif vérifié s'ajoute à `.gitleaksignore` par son empreinte ; un vrai secret se révoque, puis se retire de l'historique.

## Après la fusion et la nuit

| Workflow | Déclencheur | Contenu |
| --- | --- | --- |
| `push_main.yml` | Push sur `main` (sauf documentation et manifests) | Plan par rapport au dernier manifest ; pour chaque service modifié (serveur, client) : build de l'image, smoke test, Trivy, push par digest (`sha-<commit>`) ; puis manifest de déploiement, commité par la CD App, et tags définitifs des images (`main`, `manifest-<N>`) |
| `nightly.yml` | Chaque nuit à 1 h UTC, ou à la main | Scan Trivy des images (serveur et client) du dernier manifest, `pip-audit`, `npm audit`, gitleaks sur tout l'historique (toutes branches) |
| Dependabot | Chaque jour à 3 h (Paris), sur `main` uniquement | PR de mise à jour : actions, pip, npm, images Docker de base. Les versions majeures de `node` et les mineures de `python` sont ignorées : changement volontaire uniquement |

Une PR en brouillon ne lance que le lint et les tests unitaires. La passer en « prête » relance tout.

**Protection de `main`** : exiger uniquement le contrôle `PR status`.

## Manifests de déploiement

Chaque état déployable de `main` est décrit par un fichier `deploy/manifests/manifest-<N>-<sha7>.yaml`, validé par `deploy/manifests/schema.json`. Il fixe des versions du serveur et du client qui vont ensemble :

```yaml
schemaVersion: 2
manifestVersion: 42                 # strictement croissant
sourceRevision: <commit de main>    # 40 caractères
createdAt: 2026-10-10T16:30:00Z
services:
  server:
    kind: image
    sourceRevision: <dernier commit touchant server/>
    image: ghcr.io/tres7/kwaba-server@sha256:<digest>
  client:
    kind: image
    sourceRevision: <dernier commit touchant client/>
    image: ghcr.io/tres7/kwaba-client@sha256:<digest>
```

Les manifests v1 (client déployé depuis Git, avant le passage au VPS) restent valides ; le premier manifest v2 reconstruit l'image du client.

- Les révisions sont celles du dernier commit qui touche `server/` ou `client/`, et non celles du manifest précédent : un run sauté ne fausse rien.
- Une image n'est reconstruite que pour un service dont la révision diffère du dernier manifest ; sinon son digest est repris. Sans changement du serveur ni du client, aucun manifest n'est créé.
- L'image du client fige au build les valeurs publiques, lues dans les variables du dépôt : `PUBLIC_SITE_URL` (obligatoire, ex. `https://kwa-ba.com`), `PUBLIC_GOOGLE_CLIENT_ID`, `PUBLIC_CONTACT_EMAIL`. L'API est attendue sur `<PUBLIC_SITE_URL>/api`.
- Les scripts (`.github/scripts/manifest`, testés par `npm test`) : `plan.mjs`, `create.mjs`, `validate.mjs`, `latest.mjs`.
- Le commit du manifest sur `main` (protégée) est fait par la **CD App**, seule autorisée à contourner le ruleset. Sans elle (variable `CD_APP_CLIENT_ID` absente), le manifest est produit en artefact du run, non commité.

### Configurer la CD App

1. Profil GitHub → Settings → Developer settings → GitHub Apps → **New GitHub App** : webhook désactivé ; permission de dépôt **Contents : Read and write**, rien d'autre ; installable sur ce compte uniquement.
2. Installer l'App sur le seul dépôt `kwaba`.
3. Dans le dépôt, Settings → Secrets and variables → Actions : variable **`CD_APP_CLIENT_ID`** (Client ID de l'App) et secret **`CD_APP_PRIVATE_KEY`** (contenu du fichier `.pem` généré).
4. Ruleset « Protect main » → Bypass list : ajouter l'App.

## Tests du serveur

Les tests vivent dans `server/tests/`, et leur dossier fixe le marqueur :

| Dossier | Marqueur | Dépendances |
| --- | --- | --- |
| `tests/unit/` | `unit` | Aucune. pytest-django refuse l'accès à la base dans ces tests |
| `tests/integration/` | `integration` | PostgreSQL. RabbitMQ est simulé « en panne » : les emails passent par le repli (`mail.outbox`) |
| `tests/broker/` | `broker` | PostgreSQL et RabbitMQ réels (à venir) |

SQLite n'est pas utilisable (`SKIP LOCKED`, `DatabaseCache`, contraintes).

### Lancer les tests en local

```bash
cd server
source .venv/bin/activate
pip install -r requirements-dev.txt   # une fois

pytest -m unit                        # sans base, aucun conteneur
pytest                                # tout : démarre PostgreSQL de test si besoin
pytest -m integration                 # intégration seule
pytest tests/integration/avis         # un dossier, un fichier ou un test (::nom_du_test)
pytest -rxX                           # affiche aussi la liste des anomalies connues (xfail)
```

Les conteneurs sont démarrés **uniquement si un test en a besoin**. Le premier test qui touche la base lance `postgres-test` (`compose.test.yaml`, projet `kwaba-test`, port 55432, données en mémoire), puis l'arrête en fin de session. `pytest -m unit` ne démarre rien. La stack de développement (`compose.yaml`) n'est jamais touchée.

| Variable | Effet |
| --- | --- |
| `TEST_KEEP_SERVICES=1` | Laisse `postgres-test` démarré : les exécutions suivantes gagnent quelques secondes. Arrêt : `docker compose -f compose.test.yaml down` |
| `TEST_SERVICES=external` | Aucun conteneur : PostgreSQL est fourni par ailleurs via `POSTGRES_HOST`, `POSTGRES_PORT`, etc. (c'est le cas en CI) |

Un conteneur `postgres-test` déjà démarré est réutilisé et laissé en place. Sans Docker (sous WSL, activer l'intégration WSL de Docker Desktop), les tests d'intégration s'arrêtent avec un message explicite ; les tests unitaires tournent normalement.

Couverture comme en CI :

```bash
pytest -m unit --cov --cov-report= --cov-fail-under=0 && pytest -m integration --cov --cov-append --cov-report=
coverage report        # échoue sous le cliquet de .coveragerc
coverage html          # rapport dans htmlcov/
```

Les services hexagonaux (`messaging`, `UserService`) se testent sans base, avec les fakes en mémoire de `tests/unit/messaging/fakes.py`. Les tests de concurrence (`@pytest.mark.django_db(transaction=True)`) lancent de vrais threads sur PostgreSQL.

## Couverture

Mesurée sur `server/apps` et `server/config` (unit + integration combinés, branches comprises ; `settings.py`, `wsgi.py` et `asgi.py` exclus). Rapport dans le résumé du job, HTML en artefact `coverage-server`.

| Seuil | Règle | Où |
| --- | --- | --- |
| Cliquet global | La couverture totale ne descend jamais sous `fail_under` | `server/.coveragerc` (88 % à la mise en place) |
| Code modifié | 80 % minimum des lignes modifiées par la PR | `diff-cover` contre la branche cible |

Quand la couverture progresse, remonter `fail_under` dans la même PR. Les seuils ne s'appliquent pas aux PR en brouillon (tests unitaires seuls).

## Anomalies connues (`xfail`)

Chaque anomalie repérée a un test qui décrit le comportement attendu, marqué `@pytest.mark.xfail(strict=True, raises=AssertionError)`. Tant que le bug existe, le test est « xfail » et la CI reste verte. Le jour où le correctif arrive, le test passe, `strict=True` fait échouer la CI : retirer alors le marqueur `xfail` dans la PR du correctif.

Aucune anomalie connue à ce jour : les sept anomalies repérées à la mise en place des tests ont été corrigées.

`pytest -rxX` affiche la liste en fin d'exécution.

## Installation du poste et hook pre-push

```bash
make install    # venv du serveur, dépendances, npm ci, hooks pre-push
make help       # autres commandes : lint, test-unit, test
```

Avant chaque push : gitleaks sur les commits poussés, `ruff check`, `lint-imports` et tests unitaires si `server/` a changé, ESLint et `tsc` si `client/` a changé. La première installation compile gitleaks (quelques minutes), puis l'environnement est réutilisé.

## Lint

- Serveur : `server/ruff.toml`. Seules les règles qui révèlent des bugs sont actives (`E4`, `E7`, `E9`, `F`). Le tri des imports et `ruff format` viendront dans une PR dédiée.
- Dépendances entre modules : `server/.importlinter`, vérifié par `lint-imports` (constat A2 de `AUDIT-ARCHITECTURE.md`). Trois contrats :
  - les modules métier ne s'importent pas entre eux ; les imports existants à l'introduction de la règle sont listés dans `ignore_imports` et tolérés ;
  - `securite` et `notifications` (noyau partagé, que tous les modules peuvent importer) n'importent aucun module métier ;
  - aucun module métier n'importe `apps.notifications.infrastructure.email` : un email passe par `EmailRequestBus`.

  Un nouvel import entre deux modules métier fait échouer la PR. La liste ne doit que raccourcir : un import supprimé du code doit aussi être retiré de `ignore_imports`, sinon `lint-imports` échoue (entrée sans correspondance). Ajouter une ligne n'est acceptable qu'avec une justification dans la PR.
- Client : `client/eslint.config.mjs` (`next/core-web-vitals`, `next/typescript`), lancé par `npm run lint`.
