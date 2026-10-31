# Vérification des hôtes et des logements

N'importe qui peut créer un compte hôte. Pour protéger les voyageurs, une annonce n'est publiée qu'après la visite d'un **agent de terrain** Kwa-Ba, et une visite n'est demandée qu'une fois l'identité de l'hôte contrôlée à distance.
Code : `server/apps/verifications/` (contrôles), `server/apps/terrain/` (espace agent : file commune des missions), `client/src/app/agent/` et `client/src/components/agent/` (espace agent), `client/src/components/hote/CandidatureHote.tsx` et `VerificationIdentite.tsx` (espace hôte).

## Candidature de l'hôte

L'espace hôte affiche 3 étapes tant que l'identité n'est pas vérifiée :

1. **Téléphone** : obligatoire pour créer une annonce (l'agent appelle l'hôte), sinon `400`.
2. **Pièce d'identité** : envoyée, puis contrôlée à distance par un agent ou un admin (voir plus bas).
3. **Logement** : l'annonce reste en `en_attente`. Tant que l'identité n'est pas vérifiée, un hôte a au plus **3 annonces non vérifiées** (`MAX_ANNONCES_HOTE_NON_VERIFIE`), contre les comptes qui inondent les agents.

Badges : « Email confirmé » sur le profil (code reçu par email, rien de plus) ; « Hôte vérifié » sur la fiche d'un logement quand la pièce de l'hôte est vérifiée (`hote_verifie` dans l'API) ; « Vérifié par Kwa-Ba » sur une annonce visitée.

Refuser une candidature : dans le back-office, repasser le compte en voyageur (ou le désactiver).

## Cycle d'une annonce

| Statut (`statut_verification`) | Visible des voyageurs | Quand |
|---|---|---|
| `en_attente` | non | À la création ; après une modification de la ville, de l'adresse, de la position sur la carte ou des photos ; après une modification d'une annonce refusée |
| `verifiee` | oui (si l'hôte ne l'a pas masquée) | L'agent a validé la visite |
| `refusee` | non | L'agent a refusé, avec un motif envoyé à l'hôte |

« Visible » veut dire : recherche, villes, Concierge, Together, réservation, favoris, nouvelle conversation, fiche publique et sitemap (`HebergementModel.objects.publiees()`). L'hôte et les agents voient toujours la fiche.

Les annonces existantes au moment de la mise en place ont été marquées `verifiee` (migration `hebergements.0005`).

## Pièce d'identité de l'hôte

- Envoyée dans l'espace hôte : carte d'identité, passeport, permis ou titre de séjour, en image (ré-encodée en JPEG sans métadonnées) ou en PDF, 10 Mo maximum.
- Stockée dans un espace **privé** (`STORAGES['prive']`) : bucket R2 sans domaine public (`R2_PRIVE_BUCKET`), sinon le dossier `PRIVE_ROOT` (par défaut `server/prive/`), jamais servi par le serveur web.
- Lue uniquement par l'API (`GET /api/v1/verifications/identite/<hote>/fichier/`), pour un agent ou un administrateur. Chaque lecture est inscrite au journal d'audit (`piece_consultee`).
- Son envoi prévient les agents (« Pièce d'identité à contrôler »). Dans l'espace agent, la mission **Pièce d'identité** permet de voir le document, puis `POST /api/v1/verifications/identites/<hote>/decision/` avec `verifiee`, ou `refusee` et un motif (10 caractères au moins) envoyé à l'hôte.
- **Supprimée dès la décision** : seuls le type de pièce et le résultat du contrôle sont conservés. Une pièce refusée peut être renvoyée.
- Identité vérifiée : les annonces en attente de l'hôte sont aussitôt envoyées aux agents pour une visite (journal : `identite_verifiee` / `identite_refusee`).

## Visite de l'agent

1. Un email « Visite à planifier » part aux agents et aux administrateurs à chaque nouvelle annonce, ou à chaque annonce remise en vérification, **si l'identité de l'hôte est déjà vérifiée** (sinon, au moment où elle l'est).
2. Dans l'espace agent (téléphone), les annonces en attente des hôtes vérifiés sont des missions **Logement à visiter**, les plus anciennes d'abord. L'agent en prend une, appelle l'hôte ou lui écrit sur WhatsApp et ouvre l'itinéraire, qui mène à la position exacte placée par l'hôte ([carte](carte.md)).
3. Sur place, il coche la grille de contrôle :
   - la pièce correspond à la personne rencontrée ;
   - le logement est à l'adresse indiquée ;
   - les photos correspondent au logement ;
   - les équipements annoncés sont présents.

   Il peut ajouter jusqu'à 10 photos (stockage privé) et un commentaire.
4. **Valider** n'est possible que si tous les points sont cochés et que l'identité de l'hôte est vérifiée. Si la personne rencontrée ne correspond pas à la pièce (case décochée, refus), la pièce repasse en `refusee`. L'annonce est alors publiée et l'hôte reçoit un email ; la fiche affiche « Vérifié par Kwa-Ba ».
5. **Refuser** exige un motif d'au moins 10 caractères, envoyé à l'hôte et affiché dans son espace. L'hôte corrige l'annonce et l'enregistre : elle repart en vérification.

Chaque décision est conservée (`VisiteModel` : agent, contrôles, commentaire, photos) et inscrite au journal d'audit.

## Espace agent et file commune

`/agent` (français seulement, jamais indexé) : barre d'onglets en bas sur téléphone, menu latéral sur ordinateur.

| Page | Contenu |
|---|---|
| Accueil | Missions à prendre, les miennes, celles faites ce mois, et le détail par type |
| À faire | La file commune (filtre par type, recherche par nom, ville ou quartier), bouton **Je m'en occupe** |
| Mes missions | Mes missions en cours ; onglet **L'équipe** pour savoir qui fait quoi |
| Historique | Mes contrôles terminés (un administrateur voit ceux de toute l'équipe) |
| Fiche (`/agent/mission/<type>/<cible>`) | Qui s'en occupe, **Relâcher**, puis le contrôle lui-même |

Ce qui est à contrôler vient de chaque domaine (`server/apps/terrain/types.py`) ; une mission (`MissionModel`) naît quand un agent dit « Je m'en occupe » :

- Une mission prise disparaît de la file des autres agents. Une seule mission en cours par contrôle (contrainte en base) : deux agents qui la prennent au même instant, le second reçoit `409`.
- Seul l'agent qui l'a prise décide (`409` pour les autres agents). Il peut la **relâcher** : elle revient dans la file.
- Un **administrateur fait tout ce que fait un agent**, et en plus relâche la mission d'un autre ou décide à sa place. **Un agent ne fait jamais ce que fait un administrateur** : le back-office (`/backoffice`, `/api/v1/admin/…`) lui est refusé (`403`).
- Après la décision, la mission est close avec son issue (`validee` / `refusee`) ; décider sans l'avoir prise crée aussi une mission close, pour un historique complet.

API (agents et administrateurs, `403` sinon) : `GET /api/v1/agent/tableau/`, `GET /api/v1/agent/missions/?vue=a_faire|miennes|equipe|historique&type=&q=`, `GET /api/v1/agent/missions/<type>/<cible>/` (fiche et droits : `prendre`, `liberer`, `decider`), `POST …/prendre/`, `POST …/liberer/` (journal d'audit : `mission_prise`, `mission_relachee`). Les décisions restent celles décrites plus haut (`/api/v1/verifications/…`).

## Comptes agents

Un agent est un utilisateur avec le rôle `agent`. Ce rôle ne peut pas être choisi à l'inscription : dans l'administration Django (Utilisateurs), créer le compte, ou modifier un compte existant, avec **Rôle = Agent de terrain**. Les administrateurs ont les mêmes droits que les agents.

## Production

- `R2_PRIVE_BUCKET` : bucket R2 **privé**, distinct de celui des photos. Créé sans domaine public ; le jeton R2 existant doit y avoir accès en lecture et écriture.
- Sans ce bucket, les documents sont écrits dans `server/prive/` du conteneur et **perdus à chaque redéploiement**. À défaut de bucket, monter un volume sur `PRIVE_ROOT`.
