# Ansible : reproduire l'environnement des serveurs

Ansible décrit **ce qu'un serveur doit être** pour accueillir Kwa-Ba : la machine et ce dont l'application a besoin dessus. Il **ne déploie jamais l'application** : c'est le rôle du workflow `deploy` et de `deploy/vps/scripts/deploy.sh`.

- Ce dossier (dépôt public) contient les rôles, **sans aucun secret**.
- L'inventaire, les valeurs propres à chaque serveur et le Vault vivent dans le dépôt privé `kwa-ba/kwa-ba-infra`, cloné à côté de celui-ci (`../kwa-ba-infra`).

## Les rôles

| Rôle | Contenu | Interrupteurs (`defaults/main.yml`) |
| --- | --- | --- |
| `systeme` | Ce que fait `setup-server.sh` sur la machine : paquets de base, Docker, swap, pare-feu ufw, fail2ban, mises à jour automatiques avec redémarrage de nuit, SSH par clé uniquement | `systeme_paquets`, `systeme_docker`, `systeme_swap`, `systeme_pare_feu`, `systeme_fail2ban`, `systeme_mises_a_jour`, `systeme_ssh` |
| `proxy` | Caddy partagé par tous les projets d'un serveur (VPS personnel seulement) : `/opt/proxy`, réseau Docker `proxy`, un fichier par site, rechargement sans coupure | `proxy_actif`, `proxy_demarre`, `proxy_sites`, `proxy_volume_*` |
| `kwaba` | Ce dont l'application a besoin : utilisateur de déploiement (groupe `docker`, sans sudo), dossiers `env/` et `logs/`, `env/deploy.conf` (ce qui distingue un environnement de la prod : domaine, mode TLS, fichiers compose), fichiers de secrets `env/*.env` (depuis le Vault), clé de déploiement restreinte et porte de déploiement, tâches planifiées, rotation des journaux | `kwaba_nom`, `kwaba_racine`, `kwaba_utilisateur`, `kwaba_cle_deploiement`, `kwaba_manifest_client`, `kwaba_deploy_conf`, `kwaba_env`, `kwaba_sauvegarde`, `kwaba_renouvellement_certificats` |

Avec les valeurs par défaut, chaque fichier écrit est **identique, octet pour octet**, à celui de `setup-server.sh` : sur la prod, Ansible ne doit rien changer.

Sur le VPS personnel (plusieurs projets, SSH sur un port non standard), seul le swap du rôle `systeme` est appliqué : le pare-feu, la configuration SSH, le redémarrage automatique et le redémarrage de Docker toucheraient les autres projets.

Ni le mot de passe sudo de l'administrateur, ni les clés SSH autorisées ne sont gérés ici : `authorized_keys` de l'utilisateur de déploiement est créé vide s'il manque, jamais réécrit.

## Utilisation

Depuis ce dossier, avec le dépôt privé cloné à côté :

```bash
cd deploy/ansible
# 1. Toujours d'abord : ce qui changerait, sans rien modifier (mot de passe sudo demandé)
ansible-playbook -i ../../../kwa-ba-infra/inventory site.yml --limit production --check --diff
# 2. Seulement si le résultat est celui attendu
ansible-playbook -i ../../../kwa-ba-infra/inventory site.yml --limit production --diff
```

Règles :
- le playbook **refuse de tourner** si la copie locale de `kwa-ba-infra` n'est pas identique à `origin/main` (modifications non commitées, ou retard) : une copie ancienne réécrirait ses vieilles valeurs sur le serveur, `env/*.env` de la préprod compris. Échappatoire volontaire : `-e kwaba_inventaire_libre=true` ;
- lancé **depuis ton poste**, avec le mot de passe sudo (`become_ask_pass` dans `ansible.cfg`), **jamais depuis GitHub Actions** ;
- toujours `--check --diff` avant, et toujours `--limit` sur un seul serveur ;
- sur un serveur où le rôle touche à SSH, garde une session ouverte jusqu'à avoir vérifié qu'une nouvelle connexion fonctionne.

## Premier `--check` sur la prod : différences possibles

Le but est **zéro changement**. Les différences suivantes sont possibles au premier passage, et attendues :

- **Commentaires de `/etc/cron.d/kwaba`** : le serveur a été préparé le 13 octobre, avant la traduction des commentaires en anglais (26 octobre). Le fichier du serveur a sans doute des commentaires en français. Appliquer ne change que les commentaires.
- **Règle SSH du pare-feu** : sans le module noyau `xt_recent`, `setup-server.sh` a remplacé `limit 22/tcp` par `allow 22/tcp`. Ansible voudrait alors ajouter la règle `limit` : regarder `sudo ufw status` avant d'appliquer.
- **Paquets** : un paquet de base désinstallé à la main depuis serait réinstallé.
- **Réglage fait à la main sur le serveur** : il doit être reporté dans l'inventaire, sinon Ansible l'annule. Exemple vécu au premier `--check` : le compte `fadel`, ajouté à la main dans `AllowUsers`, aurait été retiré, et Fadel n'aurait plus pu se connecter.

Toute autre différence est à comprendre **avant** d'appliquer.

## Caddy partagé du VPS personnel (rôle `proxy`)

Un seul Caddy tient les ports 80 et 443 pour tous les projets du VPS. Il n'appartient à aucune application : déployer un projet ne le recrée jamais.

- **Ajouter un site** : un bloc dans `proxy_sites` (inventaire), puis le playbook. Caddy valide la configuration puis la recharge sans couper les autres sites ; une configuration refusée fait échouer Ansible et Caddy garde l'ancienne.
- **Raccorder un projet** : seul son service d'entrée rejoint le réseau externe `proxy` (jamais sa base ni ses workers), et le site le désigne par son **nom de conteneur**, unique sur le serveur.
- **Retirer un site** : l'enlever de `proxy_sites`, son fichier est supprimé.

### Bascule de TraderApp (une seule fois)

Aujourd'hui, le Caddy de TraderApp (`traderapp-caddy`) tient les ports 80/443. Le Caddy partagé reprend ses volumes (`traderapp_caddy_data`, `traderapp_caddy_config`) : **ses certificats sont réutilisés**, rien n'est redemandé. Coupure de quelques secondes à l'étape 3.

1. **Dépôt TraderApp** (PR prête mais pas encore déployée) : retirer le service `caddy` et `deploy/Caddyfile` ; ajouter le réseau externe `proxy` au service `server` (`networks: [default, proxy]`, avec `proxy: { external: true }`) ; retirer la recréation forcée de `caddy` dans `remote-deploy.sh` ; garder les déclarations de volumes `caddy_data` et `caddy_config` jusqu'au renommage (sinon un `docker compose down -v` pourrait les supprimer).
2. **Préparer sans démarrer** (fichiers et réseau, Caddy partagé arrêté) :
   ```bash
   ansible-playbook -i ../../../kwa-ba-infra/inventory site.yml --limit vps_perso --check --diff -e proxy_demarre=false
   ansible-playbook -i ../../../kwa-ba-infra/inventory site.yml --limit vps_perso --diff -e proxy_demarre=false
   ```
3. **Basculer** (sur le VPS, quelques secondes de coupure) :
   ```bash
   docker stop traderapp-caddy && docker rm traderapp-caddy
   docker network connect proxy traderapp_server   # en attendant le déploiement de la PR de l'étape 1
   docker compose -f /opt/proxy/compose.yml up -d
   ```
4. **Vérifier** : l'adresse de TraderApp répond, `/actuator/env` renvoie 404, et `docker logs proxy-caddy` ne montre aucune nouvelle demande de certificat.
5. **Déployer la PR de TraderApp** de l'étape 1. Avant cela, un déploiement de l'ancienne version recréerait `traderapp-caddy`, qui échouerait faute de ports libres.
6. Les playbooks suivants se lancent normalement (sans `-e proxy_demarre=false`).

Retour arrière : `docker compose -f /opt/proxy/compose.yml down`, puis redéployer la version précédente de TraderApp (son Caddy reprend les mêmes volumes).

## Secrets (Vault)

Les fichiers `env/*.env` de la préprod sont générés par le rôle `kwaba` depuis `kwaba_env` (inventaire, `group_vars/vps_perso/main.yml`), dont les secrets viennent de `group_vars/vps_perso/vault.yml`, chiffré avec le vault-id `preprod`. La prod suit le même principe (`group_vars/production/env.yml` et `vault.yml`, vault-id `production`, mot de passe distinct), `backup.env` compris : ses fichiers ont été repris du serveur par `tools/import_prod_env.py` de `kwa-ba-infra`, qui ne les affiche jamais. Sans `kwaba_env`, Ansible ne touche à aucun fichier `env/`.

Avant et après un passage d'Ansible, `scripts/env-fingerprint.sh` (sur le serveur, en tant que l'utilisateur de déploiement) donne deux empreintes de ce que lisent les conteneurs et les sauvegardes, sans afficher aucune valeur : mêmes empreintes, mêmes valeurs.

```bash
# Modifier un secret (depuis kwa-ba-infra)
EDITOR=nano ansible-vault edit --vault-id preprod@prompt inventory/group_vars/vps_perso/vault.yml
# Appliquer (depuis deploy/ansible)
ansible-playbook -i ../../../kwa-ba-infra/inventory site.yml --limit vps_perso --vault-id preprod@prompt --check --diff
ansible-playbook -i ../../../kwa-ba-infra/inventory site.yml --limit vps_perso --vault-id preprod@prompt --diff
```

- Les commandes sur la prod n'ont pas besoin de `--vault-id` : le Vault de la préprod n'est lu que pour `vps_perso`.
- Les fichiers de secrets n'affichent **jamais de diff** (il imprimerait les secrets) : seulement `changed`.
- Chaque valeur est écrite entre apostrophes, prise telle quelle par compose (un `$` reste un `$`) ; une apostrophe ou un saut de ligne dans une valeur fait échouer le playbook.
- Les conteneurs gardent les anciennes valeurs jusqu'au déploiement suivant (ou `docker compose up -d` dans `/opt/kwaba-preprod`).
- Le site `preprod.kwa-ba.com` du Caddy partagé (`proxy_sites`) demande un mot de passe au navigateur (son hash bcrypt est dans le Vault), sauf pour le webhook FedaPay, envoie `X-Robots-Tag: noindex` et retire l'en-tête `Authorization` avant nginx.

## Clé de déploiement restreinte (le serveur tire)

Avec `kwaba_cle_deploiement` (clé publique du workflow deploy), le rôle `kwaba` :

- écrit `authorized_keys` de l'utilisateur de déploiement avec cette seule clé, préfixée de `restrict,command="/usr/local/bin/<kwaba_nom>-deploy"` : ni shell, ni tunnel, ni agent, ni pty, ni copie de fichiers, quelle que soit la commande demandée ;
- installe cette porte de déploiement (propriété de root, hors du dossier qu'elle met à jour) et `git`, `rsync` ;
- la porte n'accepte que `deploy manifest-NNNN-xxxxxxx.yaml` : elle récupère `main` depuis GitHub (dépôt public, seulement `deploy/`), vérifie que le manifest y est, lit les images de `server` et de `client` (ou `clientPreprod` en préprod pour un manifest de novembre 2026 qui en a une), met à jour la configuration puis lance `scripts/deploy.sh`.

Une clé volée ne peut donc que redéployer un manifest de `main`. La prod et la préprod sont dans ce mode (prod depuis le 9 novembre 2026). Sans `kwaba_cle_deploiement`, `authorized_keys` reste tel quel. Pour passer un autre serveur à ce modèle : sa clé publique dans son `group_vars`, le playbook, puis `DEPLOY_PULL=true` dans son environnement GitHub, tout de suite après (avant, la clé n'est pas restreinte et le workflow pousse encore ; après le playbook, seul le mode tiré fonctionne).

Quand le `--check` sur la prod n'annonce plus aucun changement, `deploy/vps/scripts/setup-server.sh` peut être retiré : Ansible devient la seule description de la machine.
