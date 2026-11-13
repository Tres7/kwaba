# Titre:
Journal d'activité : qui a fait quoi, sur quoi, quand et d'où

# Status:
Accepté

# Contexte :
Le serveur enregistre déjà une soixantaine d'actions dans un journal d'audit (`securite`, table `securite_journalauditmodel`) : connexions, droits, annonces, agenda, argent, modération. Mais :
- il ne se lit que dans l'admin Django, en JSON brut ;
- le champ `utilisateur` désigne tantôt l'auteur de l'action, tantôt sa cible : on ne sait pas toujours qui a fait quoi ;
- une vingtaine d'actions n'ont pas de libellé ;
- rien n'est jamais effacé, alors que le journal contient des adresses IP (données personnelles) ;
- les connexions de tous les voyageurs noient les actions de l'équipe.

L'équipe veut un écran de back-office qui réponde vite à « qui a fait quoi, sur quoi, quand et d'où », sans surcharger les admins.

# Options
Option 1 : Améliorer l'écran de l'admin Django. Peu de travail, mais l'auteur et la cible restent confondus et l'écran reste réservé aux comptes `is_staff`.
Option 2 : Un écran de back-office qui lit la table de `securite` telle quelle. Les données restent ambiguës et `securite` grossit encore.
Option 3 : Un module `activity`, hexagonal, propriétaire du journal, avec un auteur et une cible distincts, un catalogue des actions, une conservation limitée et un écran dédié.

# Décision
Nous retenons l'option 3.

## Module `activity`
- Il rejoint le **noyau partagé** (comme `securite`, `notifications` et `export`) : tous les modules y écrivent, il ne dépend d'aucun module métier. Il lit les comptes par `get_user_model()`, comme `securite`.
- Structure hexagonale :
  - `domain/` : l'entrée du journal, l'auteur, la cible, le **catalogue des actions** (catégorie, niveau, libellé, phrase), la règle de conservation ;
  - `application/` : enregistrer, rechercher, exporter, purger ; ports (dépôt, comptes, horloge) ;
  - `infrastructure/` : modèle et dépôt Django, écrans d'administration, commande de purge.
- Interface publique : `activity.api.record(action, request=…, actor=…, target=Target(kind, id, label), **details)`. Elle ne fait jamais échouer la requête qui l'appelle.
- La table est déplacée de `securite` vers `activity` sans perte de données. `securite.audit.journaliser` disparaît ; les 85 appels passent par `activity.api.record`.

## Une entrée du journal
- Date, action, **auteur** (compte, email et rôle figés au moment de l'action ; vide pour une tâche automatique), adresse IP.
- **Cible** : type (compte, annonce, visite, réservation, signalement, réglage, objet du back-office…), identifiant et libellé figé au moment de l'action. Le journal reste lisible si l'objet change ou disparaît.
- Détails : motif, avant/après, valeurs utiles. Jamais de mot de passe, de code ni de jeton.

## Catalogue des actions
Chaque action a :
- une **catégorie** : Connexions, Droits, Annonces et vérifications, Agenda, Argent, Modération, Objets (back-office générique), Modules ;
- un **niveau** :
  - *sensible* : sécurité, droits, argent, données personnelles (compte bloqué, rôle modifié, export des finances, pièce d'identité consultée, compte de versement modifié…) ;
  - *important* : actions de l'équipe (annonce validée, visite déplacée, signalement confirmé…) ;
  - *courant* : activité normale (connexion réussie, réservation d'une visite par un hôte…) ;
- un libellé et une phrase lisible, par exemple « Rôle modifié : Jean Kouamé, voyageur → hôte ».

Une action absente du catalogue reste enregistrée et s'affiche avec son nom technique : on ne perd jamais une trace.

## Historique
Les entrées existantes sont reprises par une migration de données : l'auteur et la cible sont déduits de l'action et des détails (par exemple `role_modifie` après une visite : l'agent devient l'auteur, l'hôte la cible). Une entrée qu'on ne peut pas reprendre avec certitude garde ses données et s'affiche « ancien format ».

## Écran
Back-office > Journal d'activité :
- recherche par compte, email ou adresse IP ; période (24 h, 7 jours, 30 jours ou dates choisies) ;
- bandeau des événements sensibles du jour ;
- filtres par catégorie, avec leur nombre ; niveau « Sensibles », « Importants » (par défaut : sensibles et importants, les événements courants sont masqués) ou « Tout » ;
- liste groupée par jour : heure, icône de la catégorie, libellé, résumé, badge « Sensible », auteur ;
- fiche d'un événement : date, auteur, adresse IP, phrase complète, avant/après, et deux raccourcis « Voir l'activité de ce compte » et « Filtrer sur cette adresse IP » ;
- export CSV de la recherche en cours (10 000 lignes au plus), lui-même tracé.

## Accès
Super admins, et admins qui ont la permission spéciale « Journal d'activité » (ADR-023), accordée par un super admin. Un admin sans limite de sections ne l'a pas d'office.

## Ajout seul
Le journal reste en ajout seul pour l'application : le rôle `kwaba_app` peut ajouter une entrée, jamais la modifier ni la supprimer (`deploy/postgres/roles.sql`). Un attaquant qui prendrait la main sur l'API ne pourrait pas effacer ses traces.
- La table est renommée `activity_entry` ; `roles.sql` retire les mêmes droits sur ce nom.
- La reprise de l'historique et le déplacement de la table se font par migration, avec le rôle propriétaire.
- La conservation légale ne modifie pas les entrées : elle est notée dans une table à part (`activity_hold`), que la purge consulte.

## Conservation
- **12 mois**, puis purge automatique par une tâche quotidienne (`purge_activity`, dans le script de maintenance du VPS), lancée avec les identifiants des migrations, jamais par l'API.
- Exception : les entrées liées à un signalement sous conservation légale (modération, ADR-021) sont gardées tant que la conservation légale dure.

## Interrupteurs de modules
Hors de ce chantier. Ils passeront dans l'application (écran « Modules du site », variable d'environnement comme valeur par défaut) dans un chantier suivant ; leurs changements arriveront alors dans ce journal, catégorie Modules.

# Conséquences :
positives (bénéfices)
- On sait enfin qui a agi et sur quoi, en une phrase lisible.
- Les admins voient d'abord l'essentiel ; le reste reste à portée de filtre.
- Les adresses IP ne sont plus gardées indéfiniment.

négatifs (inconvénients)
- 85 appels à reprendre et une migration de données sur l'historique.
- Un catalogue à tenir à jour à chaque nouvelle action (une action oubliée reste visible, mais sans libellé).

Impacts futurs
- Écran « Modules du site » et son historique.
- Alertes en temps réel sur certains événements sensibles (par exemple plusieurs comptes bloqués depuis la même adresse IP).
- Complète ADR-019 (`activity` rejoint le noyau partagé), ADR-021 (conservation légale), ADR-023 (permissions spéciales) et ADR-024 (les corrections du grand livre arrivent dans ce journal).
