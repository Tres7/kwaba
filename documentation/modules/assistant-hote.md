# Assistant « Devenir hôte »

Parcours guidé pour créer une annonce : une question par écran, enregistrée au fur et à mesure, avec un pictogramme par écran. Il remplace le long formulaire pour les **nouvelles annonces** ; `HebergementForm` reste pour modifier une annonce.

Quand il est activé, `POST /api/v1/hebergements/` est réservé aux administrateurs (`403 assistant_requis`) : sinon, cette route permettrait de contourner les contrôles de l'envoi.

Activé par `MODULE_ASSISTANT_HOTE=True` ([réglages du site](reglages-site.md)). Éteint, `/hote/annonce` renvoie à l'accueil et « Nouvelle annonce » ouvre le formulaire, comme avant.

Code : `client/src/features/hebergements/assistant/` et `client/src/app/[locale]/(assistant)/`, visuels dans `client/public/hote/`, API dans `server/apps/hebergements/brouillons.py`.

## Parcours

| Phase | Écrans |
|---|---|
| Accueil | `bienvenue` |
| 1. Parlez-nous de votre logement | `phase-1`, `type`, `espace`, `adresse`, `position`, `capacite` |
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
| `photos` | moins de 5 photos |
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

`espace` (`entier`, `chambre_privee`) est un nouveau champ de l'annonce : il s'affiche sur la fiche et se filtre avec `?espace=` sur `GET /api/v1/hebergements/`.
