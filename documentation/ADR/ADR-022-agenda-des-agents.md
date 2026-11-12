# Titre:
Agenda des agents et réservation de la visite par l'hôte

# Status:
Accepté

# Contexte :
Une annonce à visiter part aujourd'hui par email à tous les agents. Ils se la répartissent dans la file commune (`terrain`), appellent l'hôte pour fixer l'heure, et l'application ne retient jamais la date de la visite. Personne ne peut donc rappeler la visite à l'hôte ou à l'agent, ni mesurer les délais.

Nous voulons que l'agent publie ses disponibilités et que l'hôte réserve lui-même un créneau, son choix valant confirmation.

Contraintes :
- monolithe modulaire strict (ADR-019) : aucun module ne lit les tables d'un autre, pas de clé étrangère entre modules ;
- les missions de terrain existent déjà (`terrain`, une seule mission en cours par cible) : un agent qui a un rendez-vous doit en avoir la mission, sinon un autre peut la prendre dans la file ;
- deux hôtes peuvent cliquer sur le même créneau au même moment ;
- une partie des hôtes n'a ni smartphone ni données : le téléphone doit rester possible.

# Options
Option 1 : Synchronisation avec Google Calendar. L'agent garde son outil, mais il faut OAuth, des jetons à renouveler et un agenda Google par agent, pour peu de gain.
Option 2 : Agenda dans l'application, dans `verifications`. Simple au départ, mais le module grossit encore et mélange décisions de visite et calcul de créneaux.
Option 3 : Un module `agenda` hexagonal (comme `messaging`), un socle `export` pour les fichiers .ics, et `verifications` qui orchestre la réservation.

# Décision
Nous retenons l'option 3.

## Trois briques
- **`export`** (socle partagé, comme `securite` et `notifications`) : briques .ics génériques (échappement, pliage des lignes, dates UTC, événement avec rappel, réponse `text/calendar`). Interface : `export/api.py`. Aucune connaissance métier. `reservations/calendrier.py` l'utilise et ne garde que ses textes.
- **`agenda`** : disponibilités des agents et rendez-vous de visite. Le modèle reste neutre (`agent_id`, `requester_id`, `targets`, dates UTC, fuseau par agenda) ; la généralisation à d'autres rendez-vous attend un second besoin réel.
- **`verifications`** : garde l'éligibilité des annonces (identité vérifiée, contrat signé) et orchestre. Il appelle `agenda.api` puis `terrain.api`. `agenda` ne connaît ni `verifications` ni `terrain`.

## Structure de `agenda`
- `domain/` : entités (plage hebdomadaire, exception, rendez-vous), exceptions métier, service pur des règles (calcul des créneaux, marge, limite par jour, durée d'un groupe, distance).
- `application/` : cas d'usage (publier ses disponibilités, réserver, déplacer, annuler, résumé de la veille, alertes), ports (`Clock`, `TransactionManager`, `Notifier`, `PeopleLookup`, dépôts), DTO.
- `infrastructure/` : ORM et dépôts Django, contrainte d'exclusion, lookups (`users.api`), notificateur (`notifications.api`), HTTP (agent, admin, flux .ics), `container.py`.
- `management/commands/agenda_worker` (`--once`, `--interval`), service `agenda` dans `deploy/vps/compose.yml`.

## Règles
- Visite d'1 h. Groupe sur un même site : 1 h + 20 min par annonce supplémentaire, 5 annonces au plus (2 h 20).
- Les durées s'affichent en heures (« 1 h 20 ») ; seules celles de moins d'une heure s'affichent en minutes (« 30 min »).
- Même site : annonces du même hôte, dans la même ville, toutes à moins de 200 m les unes des autres. L'hôte déclare le groupe, le serveur contrôle la distance ; une annonce sans position ne peut pas être groupée.
- Un groupe compte pour une visite : l'agent ne se déplace qu'une fois.
- Marge de 30 min après chaque visite. Elle est enregistrée sur le rendez-vous à la réservation (`blocked_until = end + margin`) : un changement de règle ne rallonge jamais un rendez-vous confirmé.
- Seule la visite doit tenir dans les disponibilités ; la marge peut déborder, ce qui règle la dernière visite de la journée.
- 4 visites au plus par jour et par agent. L'agent peut relever cette limite pour une date précise.
- Préavis de 24 h, horizon de 14 jours.
- Créneaux toutes les 30 min dans les plages de l'agent.
- L'hôte voit les créneaux de toute sa ville, sans nom d'agent. À la réservation, l'agent choisi est celui qui a le moins de visites ce jour-là, puis sur les 14 jours, puis par identifiant (ordre stable).
- Si un agent a déjà la mission de l'annonce, l'hôte ne voit que les créneaux de cet agent. Le déplacement reste donc chez le même agent.
- L'hôte peut déplacer son rendez-vous jusqu'à 24 h avant.
- Retirer une disponibilité n'annule jamais un rendez-vous. L'agent annule explicitement, avec un motif ; l'hôte est prévenu et la mission retourne dans la file.
- Repli par téléphone : l'agent fixe lui-même le créneau, marqué « confirmé par téléphone ». Seuls les chevauchements et la limite par jour s'appliquent.
- Visites enchaînées à des adresses différentes : hors première version, chaque annonce se réserve séparément.

## Garanties techniques
- **Pas de double réservation** : contrainte d'exclusion PostgreSQL (`btree_gist`) sur `(agenda =, [start, blocked_until) &&)`, limitée aux rendez-vous confirmés.
- **Limite par jour** : la contrainte ne la couvre pas. La réservation verrouille la ligne de l'agenda de l'agent (`SELECT … FOR UPDATE`) avant de compter, dans la même transaction que l'écriture.
- **Dates en UTC** : fuseau stocké par agenda (`Africa/Lome` par défaut), les plages sont saisies en heure locale.
- **Emails après validation** : envoyés dans `transaction.on_commit` via `notifications.api`. Pas d'outbox en première version : un email perdu se rattrape par le rappel de la veille et l'agenda dans l'application. Choix assumé.

## Liens avec les autres modules
- Réservation, déplacement, annulation, repli par téléphone et réaffectation passent par `verifications` (`appointments.py`) : il vérifie l'annonce, appelle `agenda.api`, puis prend ou relâche la mission dans `terrain`, dans la même transaction.
- La décision de visite (`verifications.decider`) marque le rendez-vous comme effectué (`agenda.api.mark_done`).
- `agenda` expose un registre de tâches périodiques (`agenda.api.register_task`), comme le registre de `paiements` : `verifications` y déclare la relance des hôtes qui ne réservent pas.

## Notifications
- « Visite à planifier » ne part plus à tous les agents. L'hôte reçoit une invitation à réserver ; les agents ne reçoivent plus que des alertes.
- Hôte : confirmation, déplacement, annulation, rappel la veille, « je suis en route ».
- Agent : un seul récapitulatif la veille au soir, trié par heure, calculé au moment de l'envoi (une visite annulée n'y figure pas), enregistré pour ne jamais partir deux fois. Il ne contient que l'heure, le nom de l'annonce, la ville et un lien.
- Agent sans disponibilité sur les 14 prochains jours : relance, au plus une fois par semaine.
- Admins : visite passée sans décision ; hôte sans rendez-vous (relance de l'hôte à 2 jours, alerte aux admins à 3 jours, avec les villes sans créneau).

## Calendriers externes
- Un fichier .ics par visite (« Ajouter à mon calendrier »), et un flux d'abonnement par agent derrière un jeton secret, révocable en le régénérant.
- Le contenu se limite au nom de l'annonce et à la ville. Adresses et téléphones restent dans l'application.
- Une visite annulée reste dans le flux avec `STATUS:CANCELLED` et le même `UID`, pour disparaître des calendriers abonnés.

# Conséquences :
positives (bénéfices)
- L'hôte connaît la date de sa visite et la choisit lui-même, sans aller-retour téléphonique.
- Les rappels, le récapitulatif et les délais deviennent possibles, car l'application sait enfin quand une visite a lieu.
- La base garantit l'absence de double réservation, même avec deux clics simultanés.
- `agenda` ne dépend d'aucun module métier : il se teste seul et se réutilisera pour d'autres rendez-vous.

négatifs (inconvénients)
- Un module de plus et un worker de plus à déployer.
- Le flux d'abonnement n'est rafraîchi par Google qu'environ toutes les 12 à 24 h : l'agenda de l'application fait foi.
- Pas de temps de trajet calculé entre deux visites : la marge fixe de 30 min sert de trajet.
- Sans outbox, un email peut se perdre si l'envoi échoue après la validation.

Impacts futurs
- Visites enchaînées à des adresses différentes chez le même agent.
- Outbox pour les emails si les pertes deviennent visibles.
- SMS ou WhatsApp pour les hôtes sans email lu.
- Complète ADR-019 (frontières des modules) : `export` rejoint le noyau partagé, `agenda` les modules métier.
