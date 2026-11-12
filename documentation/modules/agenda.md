# Agenda des agents

Les agents publient leurs disponibilités. L'hôte réserve lui-même le créneau de la visite de vérification, et son choix vaut confirmation.

Décision : [ADR-022](../ADR/ADR-022-agenda-des-agents.md). Complète la vérification des annonces ([verification.md](verification.md)).

## Où est le code

| Partie | Emplacement |
|---|---|
| Règles pures (durée, marge, limite par jour, même site, créneaux, choix de l'agent) | `server/apps/agenda/domain/rules.py` |
| Cas d'usage (disponibilités, réservation, déplacement, annulation, worker) | `server/apps/agenda/application/service.py` |
| Tables, contrainte anti-chevauchement | `server/apps/agenda/infrastructure/persistence/models.py` (`agenda_appointment_no_overlap`) |
| Emails | `server/apps/agenda/infrastructure/notifications/emails.py`, gabarits `templates/emails/agenda/` |
| API de l'agent et de l'admin, flux .ics | `server/apps/agenda/infrastructure/http/`, sous `api/v1/agenda/` |
| Interface pour les autres modules | `server/apps/agenda/api.py` |
| Réservation par l'hôte, mission, relances | `server/apps/verifications/appointments.py`, routes `api/v1/verifications/visit/` et `appointments/` |
| Briques .ics partagées | `server/apps/export/api.py` |
| Front | `client/src/features/agenda` : `admin/` pour l'espace agent (`/agent/agenda`), `HostVisit.tsx` pour l'hôte (`/hote/espace/visite`) |

## Parcours

1. L'identité de l'hôte est vérifiée (et son contrat signé s'il est demandé) : il reçoit l'email « Réservez la visite de votre logement ».
2. Il choisit un créneau parmi ceux de sa ville, tous agents confondus. L'agent le moins chargé ce jour-là reçoit la visite et sa mission dans `terrain`.
3. La veille au soir : rappel à l'hôte, récapitulatif unique à l'agent.
4. Le jour J : « Je suis en route » prévient l'hôte. La décision de visite marque le rendez-vous comme effectué.

Sans réservation : relance de l'hôte à 2 jours, alerte aux admins à 3 jours. L'agent peut aussi fixer la visite par téléphone depuis la fiche de la mission.

## Décision avant l'heure et validation sans visite

- Un agent qui décide avant l'heure de la visite prévue doit donner un motif. Le créneau est libéré, sauf pour une visite groupée dont une autre annonce attend encore.
- Back-office > Annonces > « Valider sans visite » : réservé aux super admins et à la permission spéciale « Valider une annonce sans visite ». Motif obligatoire ; l'annonce est marquée « Sans visite ».
- Par défaut, la visite prévue est annulée et la mission fermée ; l'hôte et l'agent reçoivent chacun un message.
- « Conserver la visite prévue » : elle devient un contrôle a posteriori. Sur la fiche du rendez-vous, l'agent conclut « Conforme » ou « Non conforme » ; non conforme retire l'annonce du site (statut refusée, motif envoyé à l'hôte) et alerte les admins.

## Planning des agents

Back-office > Planning des agents (`/backoffice/planning`), ouvert aux admins qui ont la section Vérifications.

- Une ligne par agent actif, avec ses villes et ses visites du jour sur sa limite (« 2/4 visites »).
- Sur une journée découpée en heures : plages de disponibilité, indisponibilités (congés, jours ou heures bloqués) et visites, colorées selon leur état (prévue, terminée, annulée, contrôle a posteriori, agent en route, fixée par téléphone).
- Navigation par jour et filtre par ville ; une visite ouvre sa fiche, d'où un admin peut la réaffecter.
- API : `GET /api/v1/admin/agenda/planning/?day=AAAA-MM-JJ&city=…`.

## Worker

`python manage.py agenda_worker` (service `agenda` en prod, `agenda-worker` en dev ; `--once` pour une seule passe, `--interval` en secondes, 300 par défaut). Une passe :

- récapitulatifs de la veille et rappels aux hôtes, à partir de l'heure réglée (18 h par défaut) ;
- relance des agents sans disponibilité sur 14 jours, une fois par semaine au plus ;
- alerte aux admins pour les visites passées sans décision ;
- tâches déclarées par les autres modules (`agenda.api.register_task`), dont la relance des hôtes de `verifications`.

## Réglages

Back-office > Réglages agenda (`/backoffice/agenda`), décision : [ADR-023](../ADR/ADR-023-reglages-agenda-et-validation-sans-visite.md).

- Ouvert aux super admins, et aux admins qui ont la permission spéciale « Réglages de l'agenda » (Utilisateurs > Droits). Un admin sans limite de sections ne l'a pas d'office.
- Valeurs par défaut dans `server/apps/agenda/domain/settings.py`, bornes vérifiées au même endroit. Sans modification, les règles validées s'appliquent.
- Une seule ligne en base (`agenda_settings`). Chaque changement va au journal d'audit (`agenda_settings_changed`, avant et après).
- Effet limité aux nouvelles réservations : un rendez-vous garde sa fin et son écart.
- Chaque réglage a un bouton d'info avec un exemple calculé sur sa valeur.

## Calendriers externes

- « Ajouter à mon calendrier » : un fichier .ics par visite.
- Abonnement : `api/proxy/v1/agenda/feed/<jeton>`, privé, révocable depuis « Mes disponibilités ». Une visite annulée y reste avec `STATUS:CANCELLED`.
- Contenu limité au nom de l'annonce et à la ville : ni adresse ni téléphone.
