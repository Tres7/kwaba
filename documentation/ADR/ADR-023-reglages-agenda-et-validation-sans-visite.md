# Titre:
Réglages de l'agenda, permissions spéciales et validation d'une annonce sans visite

# Status:
Accepté

# Contexte :
Les règles de l'agenda (ADR-022) sont écrites dans le code : préavis de 24 h, 4 visites par jour, marge de 30 min… L'équipe veut pouvoir les ajuster sans redéploiement, sans que n'importe quel admin puisse le faire.

Un admin peut déjà publier une annonce sans visite depuis le back-office. Mais le rendez-vous et la mission restent en place : l'agent irait visiter une annonce déjà en ligne, et rien n'indique qu'elle a été publiée sans contrôle sur place. De même, un agent qui décide avant l'heure de la visite garde le créneau occupé.

Contraintes :
- les droits d'un admin sont des sections (ADR et PR #226). Un admin sans limite (`admin_sections` à null) a toutes les sections : une section ne peut donc pas être « réservée aux super admins par défaut » ;
- un changement de règle ne doit jamais modifier un rendez-vous confirmé ;
- publication et annulation de la visite doivent réussir ou échouer ensemble.

# Options
Option 1 : Variables d'environnement. Déjà en place, mais il faut l'accès au serveur et un redémarrage, sans trace de qui a changé quoi.
Option 2 : Réglages en base, ouverts par une section du back-office. Un admin sans limite y aurait accès d'office.
Option 3 : Réglages en base et permissions spéciales, accordées une à une par un super admin, en plus des sections.

# Décision
Nous retenons l'option 3.

## Permissions spéciales
- Nouveau champ sur le compte : `admin_permissions`, une liste, vide par défaut. Il ne s'agit pas de sections : un admin sans limite ne les a pas.
- Deux permissions : `agenda_settings` (réglages de l'agenda) et `validate_without_visit` (valider une annonce sans visite).
- Un super admin les a toutes, et lui seul les accorde, depuis l'écran des droits d'un admin. Chaque changement va au journal d'audit.

## Réglages de l'agenda
- Une seule ligne en base (`AgendaSettingsModel`), comme les tarifs. Sans ligne, les valeurs par défaut du code s'appliquent : ce sont les règles validées. Les variables d'environnement `AGENDA_*` disparaissent.
- Bornes vérifiées par le domaine :

| Réglage | Défaut | Bornes |
|---|---|---|
| Préavis | 24 h | 1 – 72 h |
| Horizon | 14 j | 7 – 60 j |
| Visites max par jour | 4 | 1 – 10 |
| Marge entre visites | 30 min | 0 – 2 h |
| Durée de base | 1 h | 30 min – 3 h |
| Supplément par annonce | 20 min | 0 – 1 h |
| Plafond par groupe | 5 | 1 – 10 |
| Seuil « même site » | 200 m | 50 – 1000 m |
| Heure du résumé de la veille | 18 h | 12 – 22 h |
| Délai avant l'alerte « visite sans décision » | 2 h | 1 – 48 h |
| Relance de l'hôte sans réservation | 2 j | 1 – 14 j |
| Alerte aux admins | 3 j | 1 – 14 j, après la relance |

- Le pas des créneaux (30 min) reste fixe.
- Effet limité aux nouvelles réservations : un rendez-vous garde sa fin et sa marge, et le préavis, l'horizon et la limite par jour ne sont vérifiés qu'à la réservation.
- Chaque réglage a une explication avec un exemple calculé sur sa valeur.
- Audit : qui, quel réglage, ancienne et nouvelle valeur, date.
- La limite de 4 visites reste relevable par l'agent, pour une date. Pas de demande de l'hôte : il appelle, l'agent relève sa limite ou fixe la visite par téléphone.

## Décision de l'agent avant l'heure
- Si une visite est prévue plus tard, la décision demande un motif.
- Le rendez-vous passe à « effectué » avec ce motif, et son créneau est libéré : il ne bloque plus l'agenda et ne compte plus dans la limite du jour. La contrainte d'exclusion ne porte plus que sur les rendez-vous confirmés ; le domaine compte encore un rendez-vous effectué à l'heure.
- Pour une visite groupée, le rendez-vous est gardé tant qu'une autre annonce du groupe attend sa visite.

## Validation sans visite
- Réservée aux super admins et aux admins qui ont `validate_without_visit`. Motif obligatoire.
- Le statut reste `verifiee`, pour ne toucher à aucun filtre des annonces publiées. L'annonce garde la date, l'auteur et le motif de la validation sans visite, visibles en admin. Un badge côté voyageur reste une décision produit.
- Par défaut, la visite prévue est annulée : créneau libéré, mission fermée, un seul message à l'hôte et un seul à l'agent.
- Option « Conserver la visite » : le rendez-vous devient un contrôle a posteriori. L'agent est prévenu. Depuis la fiche du rendez-vous, il conclut « conforme » ou « non conforme » avec un motif. Non conforme retire l'annonce du site et alerte les admins.
- Appel direct, dans la même transaction : l'écran admin de `hebergements` appelle `verifications.api`, qui appelle `agenda.api` et `terrain.api`. Pas d'événement asynchrone : sans outbox, l'annonce pourrait être publiée sans que la visite soit annulée.

## Agent prévenu
L'agent reçoit un email quand un hôte réserve ou déplace une visite, quand une visite lui est réaffectée ou retirée, et quand un admin valide une annonce sans visite. Rien quand il fixe lui-même la visite par téléphone.

# Conséquences :
positives (bénéfices)
- L'équipe ajuste les règles sans redéploiement, dans des bornes sûres, avec une trace de chaque changement.
- Les droits sensibles ne s'étendent pas d'office à tous les admins.
- Une annonce publiée sans visite ne laisse plus de visite inutile ni de créneau bloqué, et reste repérable.

négatifs (inconvénients)
- Un champ de plus sur le compte, à gérer dans l'écran des droits.
- La contrainte d'exclusion ne couvre plus les rendez-vous effectués : seul le domaine les protège, ce qui suffit puisqu'ils ne bloquent qu'un créneau passé ou libéré.

Impacts futurs
- Badge voyageur pour les annonces validées sans visite.
- D'autres permissions spéciales pourront suivre le même modèle.
- Complète ADR-022.
