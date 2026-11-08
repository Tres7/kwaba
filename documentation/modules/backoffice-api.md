# API du back-office (administration)

Contrat entre le frontend du back-office (`client/src/app/backoffice/`) et le backend Django.
Le frontend est déjà construit sur ce contrat : les noms de champs, les codes HTTP et les formats ci-dessous doivent être respectés à l'identique.

## Règles communes

- **Préfixe** : toutes les routes sont sous `/api/v1/admin/`.
- **Accès** : utilisateur authentifié (JWT) **et** `role == "admin"`. Sinon : `401` (non connecté) ou `403` `{"detail": "Accès réservé aux administrateurs."}`.
  Utiliser `permission_classes = [EstAdministrateur]` (`apps/securite/permissions.py`) sur **chaque** vue : le rôle est lu en base à chaque requête. Ne jamais se fier au rôle de la session NextAuth ni à un rôle envoyé par le client ; la redirection du middleware Next.js n'est qu'un confort d'affichage, pas une protection.
- **Droits des admins** : un super admin (`is_superuser`, les deux directeurs) a tous les droits. Un admin peut être limité à des sections (`admin_sections`, `null` : toutes) : `EstAdministrateur` retrouve la section d'après l'URL (`SECTIONS_ADMIN` et `_ROUTES_SECTIONS` dans `apps/securite/permissions.py`) et répond `403` `{"detail": "Cette section ne vous est pas ouverte."}`. Une nouvelle route doit y être rattachée : un test échoue sinon, et elle est refusée aux admins limités. La section `verifications` couvre aussi l'espace agent.
- **Admin temporaire** : à `admin_expire_le`, le compte retrouve `role_avant_admin` (`voyageur` s'il est vide), dès sa première requête (`AuthentificationJWT`) ou par la tâche quotidienne (`retirer_admins_expires`).
- **Super admins** : jamais gérés par l'API. Ils se nomment et se retirent sur le serveur : `manage.py super_admin <email> [--retirer]` (sur un compte existant ; le dernier ne peut pas être retiré).
- **Pagination** des listes : paramètres `page` (défaut 1) et `page_size` (défaut 20, maximum 100). Réponse :
  ```json
  { "results": [ ... ], "count": 134, "page": 1, "page_size": 20 }
  ```
  `count` = nombre total d'éléments après filtres. Une page au-delà de la dernière renvoie `results: []` (pas d'erreur).
- **Tri** : du plus récent au plus ancien, sauf mention contraire.
- **Erreurs** : format DRF habituel, `{"detail": "..."}` ou `{"champ": ["message"]}`. Messages en français, affichés tels quels à l'admin.
- **Dates** : ISO 8601 (`2026-10-06` pour les dates, `2026-10-06T14:03:00Z` pour les horodatages). **Montants** : nombres (pas de chaînes), en FCFA.
- **Journal** : chaque action d'écriture (PATCH, POST, DELETE) est tracée dans le journal d'audit (`apps.securite`, `JournalAuditModel` : admin, action, cible et motif dans `details`, date), consultable dans l'administration Django.
- **Implémentation** : `server/apps/backoffice/` ; tests : `server/tests/integration/backoffice/`.

## 1. Tableau de bord

### `GET /api/v1/admin/stats/`

```json
{
  "utilisateurs": { "total": 152, "nouveaux_30j": 18, "hotes": 23, "desactives": 2 },
  "annonces": { "total": 41, "visibles": 37, "verifiees": 12 },
  "reservations": { "confirmees_30j": 64, "annulees_30j": 5, "volume_30j": 5840000 },
  "avis": { "total": 88, "moyenne": 4.6 },
  "reservations_par_jour": [
    { "date": "2026-09-07", "nombre": 3, "volume": 270000 }
  ]
}
```

- `volume_30j` : somme des `total_price` des réservations **confirmées** créées sur les 30 derniers jours.
- `reservations_par_jour` : **exactement 30 entrées**, une par jour (du plus ancien au plus récent, aujourd'hui inclus), `nombre` et `volume` à 0 les jours sans réservation. Réservations confirmées uniquement, par date de création.
- `avis.moyenne` : `null` s'il n'y a aucun avis.

## 2. Utilisateurs

### `GET /api/v1/admin/users/`

Filtres (tous optionnels) :

| Paramètre | Valeurs | Effet |
|---|---|---|
| `q` | texte | recherche insensible à la casse dans email, prénom, nom, téléphone |
| `role` | `voyageur` \| `hote` \| `agent` \| `admin` | |
| `actif` | `true` \| `false` | filtre sur `is_active` |

Élément :
```json
{
  "id": "uuid", "email": "ama@exemple.com", "first_name": "Ama", "last_name": "Koffi",
  "role": "hote", "phone": "+22890000000", "avatar_url": null,
  "is_verified": true, "is_active": true,
  "date_joined": "2026-03-11T21:07:00Z", "last_login": null,
  "nb_reservations": 3, "nb_annonces": 2
}
```
`nb_reservations` : réservations faites en tant que voyageur (toutes statuts). `nb_annonces` : hébergements dont il est l'hôte.

### `PATCH /api/v1/admin/users/<uuid>/`

Corps (un ou plusieurs champs) : `{ "is_active": false }`, `{ "role": "hote" }`.

- Renvoie l'utilisateur mis à jour (même format que la liste), `200`.
- Super admin seulement : `{ "admin_sections": ["avis", "finances"] }` (`null` : toutes), `{ "admin_expire_le": "2026-12-01T18:00:00Z" }` (date à venir avec fuseau, `null` : sans fin). Ces champs ne s'appliquent qu'à un admin, et peuvent accompagner `{ "role": "admin" }`.
- `403` `{"detail": "Vous ne pouvez pas modifier votre propre compte."}` si l'admin se cible lui-même.
- `403` si la cible est un super admin, pour tout le monde.
- `403` pour un admin simple dès que le compte ciblé est admin, ou que la demande en fait un admin.
- `400` si `role` n'est pas `voyageur`, `hote`, `agent` ou `admin`.
- `404` si l'utilisateur n'existe pas.
- Désactiver un compte (`is_active: false`) doit l'empêcher de se connecter (déjà géré par le login) **et invalider ses refresh tokens** si la blacklist SimpleJWT est activée.

## 3. Annonces

### `GET /api/v1/admin/hebergements/`

Filtres : `q` (nom, ville, quartier, email de l'hôte), `ville` (exacte, insensible à la casse), `visible` (`true`/`false` → `is_available`), `verifie` (`true`/`false` → `statut_verification == "verifiee"`).

Élément :
```json
{
  "id": "uuid", "name": "Villa Hibiscus", "type": "villa", "city": "Assinie", "location": "Bord de lagune",
  "price_per_night": 125000, "image_url": "https://...", "is_available": true, "est_verifie": false, "statut_verification": "en_attente",
  "rating": 4.8, "review_count": 12, "nb_reservations": 9,
  "host": { "id": "uuid", "nom": "Kossi Mensah", "email": "hote@exemple.com" },
  "created_at": "2026-10-03T19:00:00Z"
}
```

### `PATCH /api/v1/admin/hebergements/<uuid>/`

Corps : `{ "is_available": false }` (masquer / republier), `{ "est_verifie": true }` (valider sans visite : `statut_verification = "verifiee"`, l'annonce est publiée) ou `{ "est_verifie": false }` (retour en `en_attente` : l'annonce quitte le site et les agents sont prévenus qu'une visite est à faire). Renvoie l'annonce (format liste), `200`. `404` si inconnue.

### `DELETE /api/v1/admin/hebergements/<uuid>/?motif=...`

`motif` en paramètre d'URL, obligatoire (5 à 500 caractères), tracé dans le journal ; `400` s'il manque.
`204`. Supprime l'annonce (cascade : réservations, avis, conversations, fermetures de calendrier). `404` si inconnue. `409` si des paiements y sont liés (à masquer plutôt).

### `est_verifie`

Pas de champ dédié : `est_verifie` est calculé à partir de `statut_verification` (vérification par les agents de terrain, `apps/verifications`). Seule une annonce vérifiée et visible est publiée ; le badge public « Vérifié par Kwa-Ba » en découle.

## 4. Réservations

### `GET /api/v1/admin/reservations/`

Filtres : `q` (référence, nom de l'annonce, email du voyageur), `statut` (`pending` \| `confirmed` \| `cancelled`), `debut` et `fin` (AAAA-MM-JJ : séjours qui chevauchent la période, c.-à-d. `check_in < fin` et `check_out > debut`).

Élément :
```json
{
  "id": "uuid", "reference": "RES-AF2026-3A43",
  "hebergement": { "id": "uuid", "name": "Suite Océan", "city": "Dakar" },
  "voyageur": { "id": "uuid", "nom": "Kofi Test", "email": "kofi@exemple.com" },
  "hote": { "id": "uuid", "nom": "Kossi Mensah" },
  "check_in": "2026-11-10", "check_out": "2026-11-13", "nights": 3, "guests_count": 2,
  "total_price": 291600, "status": "confirmed", "payment_method": "mobile_money",
  "created_at": "2026-10-05T10:00:00Z"
}
```

### `POST /api/v1/admin/reservations/<uuid>/annuler/`

Corps : `{ "motif": "Doublon signalé par l'hôte" }` (obligatoire, 5 à 500 caractères).
- `200` avec la réservation mise à jour (`status: "cancelled"`).
- `400` `{"detail": "Cette réservation est déjà annulée."}` si déjà annulée.
- Contrairement à l'annulation par le voyageur, **autorisée même si le séjour a commencé**.
- Annulation « par Kwa-Ba » (`annule_par = "plateforme"`) : un voyageur qui a payé est remboursé en totalité et le versement à l'hôte est annulé (`paiements.services.annuler`).

## 5. Avis

### `GET /api/v1/admin/avis/`

Filtres : `q` (commentaire, nom de l'annonce, email de l'auteur), `note` (1 à 5).

Élément :
```json
{
  "id": "uuid", "note": 2, "commentaire": "...",
  "auteur": { "id": "uuid", "nom": "Awa Traoré", "email": "awa@exemple.com" },
  "hebergement": { "id": "uuid", "name": "Riad Jasmin" },
  "reponse_hote": "", "created_at": "2026-10-05T19:26:55Z"
}
```

### `DELETE /api/v1/admin/avis/<uuid>/?motif=...`

`motif` en paramètre d'URL, obligatoire (5 à 500 caractères), tracé dans le journal.
`204`. La note de l'hébergement est recalculée (déjà assuré par le signal `post_delete` de l'app `avis`).

## Récapitulatif

| Méthode | Route | Usage |
|---|---|---|
| GET | `/admin/stats/` | tableau de bord |
| GET | `/admin/users/` | liste des comptes |
| PATCH | `/admin/users/<id>/` | activer / désactiver, changer le rôle, droits d'un admin |
| GET | `/admin/droits/` | droits de l'admin connecté (ouvert à tous les admins) |
| GET | `/admin/hebergements/` | liste des annonces |
| PATCH | `/admin/hebergements/<id>/` | masquer / publier, vérifier |
| DELETE | `/admin/hebergements/<id>/?motif=` | supprimer une annonce |
| GET | `/admin/reservations/` | liste des réservations |
| POST | `/admin/reservations/<id>/annuler/` | annulation par l'admin |
| GET | `/admin/avis/` | liste des avis |
| DELETE | `/admin/avis/<id>/?motif=` | modération d'un avis |

Créer un compte admin : `docker compose exec backend python manage.py createsuperuser` (le manager donne automatiquement `role = admin`).
