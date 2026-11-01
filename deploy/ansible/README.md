# Ansible : reproduire l'environnement des serveurs

Ansible décrit **ce qu'un serveur doit être** pour accueillir Kwa-Ba : la machine et ce dont l'application a besoin dessus. Il **ne déploie jamais l'application** : c'est le rôle du workflow `deploy` et de `deploy/vps/scripts/deploy.sh`.

- Ce dossier (dépôt public) contient les rôles, **sans aucun secret**.
- L'inventaire, les valeurs propres à chaque serveur et le Vault vivent dans le dépôt privé `Tres7/kwa-ba-infra`, cloné à côté de celui-ci (`../kwa-ba-infra`).

## Les rôles

| Rôle | Contenu | Interrupteurs (`defaults/main.yml`) |
| --- | --- | --- |
| `systeme` | Ce que fait `setup-server.sh` sur la machine : paquets de base, Docker, swap, pare-feu ufw, fail2ban, mises à jour automatiques avec redémarrage de nuit, SSH par clé uniquement | `systeme_paquets`, `systeme_docker`, `systeme_swap`, `systeme_pare_feu`, `systeme_fail2ban`, `systeme_mises_a_jour`, `systeme_ssh` |
| `proxy` | Caddy partagé par tous les projets d'un serveur (VPS personnel seulement) : `/opt/proxy`, réseau Docker `proxy`, un fichier par site, rechargement sans coupure | `proxy_actif`, `proxy_demarre`, `proxy_sites`, `proxy_volume_*` |
| `kwaba` | Ce dont l'application a besoin : utilisateur de déploiement (groupe `docker`, sans sudo), dossiers `env/` et `logs/`, tâches planifiées, rotation des journaux | `kwaba_nom`, `kwaba_racine`, `kwaba_utilisateur`, `kwaba_sauvegarde`, `kwaba_renouvellement_certificats` |

Avec les valeurs par défaut, chaque fichier écrit est **identique, octet pour octet**, à celui de `setup-server.sh` : sur la prod, Ansible ne doit rien changer.

Sur le VPS personnel (plusieurs projets, SSH sur le port 2222), seul le swap du rôle `systeme` est appliqué : le pare-feu, la configuration SSH, le redémarrage automatique et le redémarrage de Docker toucheraient les autres projets.

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
4. **Vérifier** : `https://217-154-19-172.sslip.io` répond, `/actuator/env` renvoie 404, et `docker logs proxy-caddy` ne montre aucune nouvelle demande de certificat.
5. **Déployer la PR de TraderApp** de l'étape 1. Avant cela, un déploiement de l'ancienne version recréerait `traderapp-caddy`, qui échouerait faute de ports libres.
6. Les playbooks suivants se lancent normalement (sans `-e proxy_demarre=false`).

Retour arrière : `docker compose -f /opt/proxy/compose.yml down`, puis redéployer la version précédente de TraderApp (son Caddy reprend les mêmes volumes).

## Ce qui viendra ensuite

- fichiers `env/*.env` et `deploy.conf` générés depuis le Vault ;
- clé de déploiement restreinte (`restrict,command=…` : seuls `rsync` et `deploy.sh`), en prod comme en préprod.

Quand le `--check` sur la prod n'annonce plus aucun changement, `deploy/vps/scripts/setup-server.sh` peut être retiré : Ansible devient la seule description de la machine.
