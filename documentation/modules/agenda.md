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

## Worker

`python manage.py agenda_worker` (service `agenda` en prod, `agenda-worker` en dev ; `--once` pour une seule passe, `--interval` en secondes, 300 par défaut). Une passe :

- récapitulatifs de la veille et rappels aux hôtes, à partir de `AGENDA_DIGEST_HOUR` ;
- relance des agents sans disponibilité sur 14 jours, une fois par semaine au plus ;
- alerte aux admins pour les visites passées sans décision ;
- tâches déclarées par les autres modules (`agenda.api.register_task`), dont la relance des hôtes de `verifications`.

## Réglages

Variables d'environnement, avec leur valeur par défaut :

| Variable | Défaut | Rôle |
|---|---|---|
| `AGENDA_TIMEZONE` | `Africa/Lome` | fuseau des emails d'alerte |
| `AGENDA_VISIT_DURATION_MIN` | 60 | durée d'une visite |
| `AGENDA_EXTRA_LISTING_MIN` | 20 | par annonce en plus dans une visite groupée |
| `AGENDA_MAX_LISTINGS` | 5 | annonces par visite groupée |
| `AGENDA_MARGIN_MIN` | 30 | écart avant la visite suivante |
| `AGENDA_MAX_PER_DAY` | 4 | visites par jour et par agent |
| `AGENDA_PER_DAY_CEILING` | 10 | limite maximale qu'un agent peut fixer pour une journée |
| `AGENDA_NOTICE_H` | 24 | préavis de réservation et de déplacement |
| `AGENDA_HORIZON_DAYS` | 14 | horizon de réservation |
| `AGENDA_STEP_MIN` | 30 | pas des créneaux proposés |
| `AGENDA_SAME_SITE_DISTANCE_M` | 200 | distance maximale d'une visite groupée |
| `AGENDA_DIGEST_HOUR` | 18 | heure locale des récapitulatifs et rappels |
| `AGENDA_DECISION_DELAY_H` | 2 | délai avant l'alerte « visite sans décision » |
| `AGENDA_HOST_REMINDER_DAYS` | 2 | relance de l'hôte sans réservation |
| `AGENDA_HOST_ALERT_DAYS` | 3 | alerte aux admins |

## Calendriers externes

- « Ajouter à mon calendrier » : un fichier .ics par visite.
- Abonnement : `api/proxy/v1/agenda/feed/<jeton>`, privé, révocable depuis « Mes disponibilités ». Une visite annulée y reste avec `STATUS:CANCELLED`.
- Contenu limité au nom de l'annonce et à la ville : ni adresse ni téléphone.
