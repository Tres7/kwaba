# Kwa-Ba Together (voyages de groupe)

Préparer un voyage à plusieurs sans tout gérer dans une conversation WhatsApp.
Code : `server/apps/voyages/` (backend), `client/src/app/(main)/together/` et `client/src/components/voyage/ProposerAuGroupe.tsx` (frontend).

## Fonctionnement

| Fonction | Qui | Détail |
|---|---|---|
| Créer un voyage | Tout utilisateur connecté | Nom, destination, dates (facultatives), nombre de voyageurs ; le créateur devient organisateur |
| Inviter | Membres | Lien `/together/rejoindre/<code>` à partager (bouton WhatsApp) ; l'organisateur peut désactiver le lien et en créer un nouveau |
| Proposer un logement | Membres | Depuis le voyage (recherche filtrée sur les dates) ou depuis une fiche logement (« Proposer à mon groupe ») |
| Voter | Membres | Un vote par membre, modifiable ; les propositions sont triées par nombre de votes |
| Budget par personne | Calculé | Prix des nuits pour les dates du voyage, frais de service et de ménage compris (taux du back-office), divisé par le nombre de voyageurs ; disponibilité et capacité affichées |
| Retenir un logement | Organisateur | Bouton « Réserver pour le groupe » (dates et voyageurs préremplis) |
| Itinéraire | Membres | Étapes datées (heure, lieu, détails), regroupées par jour |
| Réservations et infos | Membres | Chacun peut partager ses propres réservations Kwa-Ba ; bloc « infos pratiques » commun (vols, rendez-vous) |
| Payer pour le groupe | Personne qui a réservé / membres | Sur une réservation partagée en attente de paiement, la personne qui a réservé « demande au groupe de payer » ; chaque autre membre voit alors « Payer pour le groupe » et peut payer le séjour entier à sa place (paiement par un tiers, voir `documentation/modules/paiements.md`) |
| Membres | Organisateur / membre | Retirer un membre / quitter ; l'organisateur ne peut que supprimer le voyage |

Limites : 20 membres par voyage. Un voyage est invisible (404) pour qui n'en est pas membre. Les membres ne voient que le prénom et l'initiale du nom des autres.

La page d'un voyage se rafraîchit toutes les 15 secondes (votes et propositions des autres membres). Pas de temps réel par WebSocket pour l'instant.

## API (`/api/v1/voyages/`)

| Méthode | Route | Rôle |
|---|---|---|
| GET / POST | `` | Mes voyages / créer |
| GET / PATCH / DELETE | `<id>/` | Détail complet / modifier (les membres ne peuvent changer que `notes`) / supprimer (organisateur) |
| GET / POST | `invitations/<code>/` | Aperçu avant de rejoindre / rejoindre |
| POST | `<id>/nouveau-lien/` | Nouveau code d'invitation (organisateur) |
| DELETE | `<id>/membres/<user_id>/` | Quitter ou retirer un membre |
| POST / DELETE | `<id>/propositions/`, `<id>/propositions/<pid>/` | Proposer / retirer un logement |
| POST / DELETE | `<id>/vote/` | Voter `{proposition}` / retirer son vote |
| POST | `<id>/retenir/` | Logement retenu `{proposition}` ou `null` (organisateur) |
| POST / DELETE | `<id>/etapes/`, `<id>/etapes/<eid>/` | Itinéraire |
| POST / DELETE | `<id>/reservations/`, `<id>/reservations/<lid>/` | Partager une de ses réservations / ne plus la partager |
| POST / DELETE | `<id>/reservations/<lid>/demande-paiement/` | Demander au groupe de payer sa réservation / ne plus le demander (la personne qui a réservé) |
| GET / POST | `<id>/reservations/<lid>/paiement/` | Ce que paie le membre / démarrer son paiement `{moyen}` |

Le détail renvoie tout le voyage en une fois (membres, propositions avec votes et budget, itinéraire, réservations partagées).

## Prochaines étapes possibles

- Répartition des paiements entre membres (chacun paie sa part). Aujourd'hui, un membre peut payer le séjour entier à la place de la personne qui a réservé.
- Notifications (nouveau membre, nouvelle proposition, logement retenu).
- Temps réel (WebSocket) à la place du rafraîchissement périodique.

## Tests

`server/tests/integration/voyages/test_together.py` : invitation, confidentialité, votes et budget par personne, droits de l'organisateur, itinéraire, réservations partagées, départ d'un membre, nouveau lien. Paiement pour le groupe : `server/tests/integration/reservations/test_paiement_tiers.py`.
