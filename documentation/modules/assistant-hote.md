# Assistant « Devenir hôte »

Parcours guidé pour créer une annonce : une question par écran, enregistrée au fur et à mesure, avec un pictogramme par écran. Il remplace le long formulaire pour les **nouvelles annonces** ; `HebergementForm` reste pour modifier une annonce.

Quand il est activé, `POST /api/v1/hebergements/` est réservé aux administrateurs (`403 assistant_requis`) : sinon, cette route permettrait de contourner les contrôles de l'envoi.

Activé par `MODULE_ASSISTANT_HOTE=True` ([réglages du site](reglages-site.md)). Éteint, `/hote/annonce` renvoie à l'accueil et « Nouvelle annonce » ouvre le formulaire, comme avant.

Code : `client/src/features/hebergements/assistant/` et `client/src/app/[locale]/(assistant)/`, visuels dans `client/public/hote/`, API dans `server/apps/hebergements/brouillons.py`.

## Parcours

| Phase | Écrans |
|---|---|
| Accueil | `bienvenue` |
| 1. Parlez-nous de votre logement | `phase-1`, `type`, `adresse`, `position`, `capacite` |
| 2. Faites-le sortir du lot | `phase-2`, `equipements`, `photos`, `titre`, `description` |
| 3. Terminez et publiez | `phase-3`, `prix`, `regles`, `accueil`, `securite`, `telephone`, `identite`, `versement`, `contrat`, `recapitulatif` |

La liste des écrans, leurs visuels et la condition pour continuer sont dans `assistant/etapes.ts`. L'adresse donne l'écran (`/hote/annonce/<brouillon>?etape=photos`), donc le bouton Retour du téléphone fonctionne. Une adresse tapée à la main ne saute aucune question : `etapeAffichee` ramène au premier écran sans réponse.

## Brouillon

- `/hote/annonce/nouvelle` crée le brouillon dès le premier écran.
- Chaque réponse part en arrière-plan (`useBrouillonAssistant`), une requête à la fois, après une pause de saisie ou au bouton Suivant.
- Sans réseau, les réponses restent dans la page et repartent seules : au retour du réseau, ou toutes les 10 secondes.
- `PATCH /api/v1/hebergements/brouillons/<id>/` avec `{donnees, etape}` fusionne les réponses, enregistre l'écran atteint et renvoie `erreurs` : ce que l'API refuserait à l'envoi, comme des coordonnées dans la description. C'est une information affichée à l'hôte, jamais un refus d'enregistrer.

## Envoi pour vérification

`POST /api/v1/hebergements/brouillons/<id>/soumettre/` (`soumission.py`) contrôle tout à nouveau, côté serveur, dans une seule transaction : l'annonce est créée, ses photos lui sont rattachées et le brouillon est supprimé, ou rien ne se passe. Un double clic ne crée pas deux annonces.

| Condition | Refus si |
|---|---|
| `photos` | moins de 5 photos (20 au plus par annonce) |
| `photos_du_compte` | une photo n'a pas été envoyée par cet hôte (image d'un autre hôte, image externe) |
| `attestation` | l'hôte n'a pas certifié ses informations ; la date est conservée (`attestation_le`) |
| `telephone` | pas de numéro |
| `identite` | pièce absente ou refusée ; une pièce en cours de contrôle suffit |
| `versement` | pas de compte Mobile Money |
| `preinscription` | pré-inscription non acceptée, pendant le pré-lancement |

`GET …/conditions/` renvoie cet état et la liste `bloquants`, pour l'affichage. Le contrat hôte ne bloque pas l'envoi : sans signature, les agents ne visitent simplement pas encore le logement. L'annonce passe ensuite par le circuit habituel ([vérification](verification.md)).

Les déclarations (`cameras`, `animaux`, `travaux`) sont conservées avec l'annonce. Sur sa fiche Pièce d'identité, l'agent voit le titulaire du compte de versement, à comparer au nom de la pièce.

## Écrans et visuels

- **Disposition** : sur ordinateur, le pictogramme à gauche et la question à droite ; sur téléphone, le pictogramme en haut et une feuille blanche par-dessus. La carte et les photos ont besoin de place : pas de visuel sur téléphone.
- **Visuels** : un pictogramme de la bibliothèque du site (lucide) sur une tuile à la couleur de la phase (vert, orange, vert foncé), devant un motif géométrique discret dessiné en SVG (`Decor.tsx`). Rien à télécharger. Les images 3D générées par IA du début ont été retirées : elles se reconnaissaient comme telles, ce qui coûte de la confiance dans un parcours où l'hôte confie sa pièce d'identité. Pas d'image générée dans ce parcours.
- **Mouvement** : la tuile flotte doucement et l'écran entre sur le côté (classes `assistant-*` de `globals.css`). Tout s'arrête avec `prefers-reduced-motion`.

## Types de logement et capacité

Taxonomie Kwa-Ba (brief AN-TAX du 3 novembre 2026), les mots employés à Lomé, sans T1/T2 ni surface : `chambre_privee`, `studio`, `appartement`, `maison_entiere`, `villa`, `chambre_hotel`, plus `residence` et `auberge`, gardés par l'équipe. Les anciens `maison` et `hotel` sont devenus `maison_entiere` et `chambre_hotel` (migration `hebergements.0018`) ; `?type=hotel` et `?type=maison` marchent encore dans la recherche. Libellés et pictogrammes : `client/src/components/hebergement/TypeLogement.tsx`. Sur une carte et sur la fiche, le nom de la langue de la page est en grand et l'autre dans un petit badge (« Appartement » + « Apartment »).

- `espace` (`entier`, `chambre_privee`) suit le type (`HebergementModel.save()`) : plus de question à part. Il se filtre encore avec `?espace=`.
- **Obligatoires pour une nouvelle annonce** : voyageurs (1 à 20), chambres (0 pour un studio), salles de bain (1 au moins), un lit au moins et le **point de repère** (« Derrière le CHU Sylvanus Olympio, Tokoin », 200 caractères, sans coordonnées). La surface n'est plus demandée ni affichée (colonne `surface_m2` gardée jusqu'à une prochaine version).
- **Point de repère** : presque l'adresse exacte, donc jamais sur l'annonce publique. L'agent le voit pour la visite, le voyageur dans sa réservation une fois payée (`point_repere` de `GET /api/v1/reservations/`).

## Hôtels, résidences et auberges

Pour `chambre_hotel`, `residence` et `auberge` (`HebergementModel.ETABLISSEMENTS`), l'assistant suit un autre chemin (`pour` dans `etapes.ts`) :

- **Écran « Vos chambres »** (`chambres`) à la place de « Capacité » : une ligne par type de chambre (nom, prix par nuit, nombre de chambres identiques jusqu'à 500, personnes par chambre). Un hôtel de 200 chambres se décrit en quelques lignes.
- **Pas d'écran de prix** : chaque type a le sien. L'annonce affiche le moins cher (« à partir de ») et la plus grande capacité.
- **Pièces des photos** : les espaces de l'établissement (Réception, Chambres, Restaurant, Bar, Piscine, Salle de sport, Salle de réunion…), pas « Chambre 1, Chambre 2 ». Les photos de chaque type s'ajoutent ensuite dans l'espace hôte, « Types de chambres ».
- **API** : `types_chambres` (écriture seule) crée les `TypeLogementModel` avec l'annonce ; chambres, salles de bain et lits ne sont pas demandés. Sans `types_chambres`, l'annonce garde un seul type « Chambre ». Une maison ignore `types_chambres`.

## Chambres vendues ailleurs

Un hôtel vend aussi ses chambres à la réception ou sur d'autres sites. Dans son calendrier, il ferme un type entier ou **seulement quelques chambres** d'un type sur des dates (`quantite` d'un `BlocageModel`) : elles comptent comme prises, les autres restent réservables. Une fermeture partielle est possible à côté de réservations, dans la limite des chambres encore libres chaque nuit (`409` sinon), et plusieurs fermetures partielles s'additionnent.

## Pièce de chaque photo

Sous chaque photo, l'hôte choisit la pièce : Chambre 1, Chambre 2… (selon son nombre de chambres ; « Pièce principale » pour un studio), Salon, Cuisine, Salle à manger, Salle de bain 1…, Toilettes, Terrasse, Balcon, Jardin ou cour, Piscine, Extérieur, Entrée, Vue, Parking, Autre. Codes et ordre : `client/src/features/hebergements/pieces.ts`, liste acceptée par l'API : `PIECES` de `server/apps/hebergements/serializers.py`.

- `legendes_photos` (`{url: code}`) : **obligatoire pour chaque photo** d'une nouvelle annonce (`400` sinon) ; l'écran Photos de l'assistant attend que chaque photo ait sa pièce. Les pièces des photos retirées sont oubliées.
- Les annonces plus anciennes s'affichent sans pièces (`{}`) et se modifient sans les donner.
- **Voyageurs** : la pièce s'affiche sur chaque photo de la galerie, et la section « Les pièces en photos » montre toutes les photos rangées par pièce. **Agent** : sous chaque photo de la fiche de visite.
