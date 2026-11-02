# Assistant « Devenir hôte »

Parcours guidé pour créer une annonce : une question par écran, enregistrée au fur et à mesure, avec une miniature 3D par écran. Il remplace le long formulaire pour les **nouvelles annonces** ; `HebergementForm` reste pour modifier une annonce.

Activé par `MODULE_ASSISTANT_HOTE=True` ([réglages du site](reglages-site.md)). Éteint, `/hote/annonce` renvoie à l'accueil et « Nouvelle annonce » ouvre le formulaire, comme avant.

Code : `client/src/features/hebergements/assistant/` et `client/src/app/[locale]/(assistant)/`, visuels dans `client/public/hote/`, API dans `server/apps/hebergements/brouillons.py`.

## Parcours

| Phase | Écrans |
|---|---|
| Accueil | `bienvenue` |
| 1. Parlez-nous de votre logement | `phase-1`, `type`, `espace`, `adresse`, `position`, `capacite` |
| 2. Faites-le sortir du lot | `phase-2`, `equipements`, `photos`, `titre`, `description` |
| Suite | `fin`, puis le formulaire pour le prix, les règles et l'envoi |

La liste des écrans, leurs visuels et la condition pour continuer sont dans `assistant/etapes.ts`. L'adresse donne l'écran (`/hote/annonce/<brouillon>?etape=photos`), donc le bouton Retour du téléphone fonctionne. Une adresse tapée à la main ne saute aucune question : `etapeAffichee` ramène au premier écran sans réponse.

## Brouillon

- `/hote/annonce/nouvelle` crée le brouillon dès le premier écran.
- Chaque réponse part en arrière-plan (`useBrouillonAssistant`), une requête à la fois, après une pause de saisie ou au bouton Suivant.
- Sans réseau, les réponses restent dans la page et repartent seules : au retour du réseau, ou toutes les 10 secondes.
- `PATCH /api/v1/hebergements/brouillons/<id>/` avec `{donnees, etape}` fusionne les réponses, enregistre l'écran atteint et renvoie `erreurs` : ce que l'API refuserait à l'envoi, comme des coordonnées dans la description. C'est une information affichée à l'hôte, jamais un refus d'enregistrer.

Les conditions de l'assistant aident l'hôte, elles ne protègent rien : le contrôle définitif reste celui de `POST /api/v1/hebergements/`.

## Écrans et visuels

- **Disposition** : sur ordinateur, la miniature à gauche et la question à droite ; sur téléphone, la miniature en haut et une feuille blanche par-dessus. La carte et les photos ont besoin de place : pas de visuel sur téléphone.
- **Mouvement** : la miniature flotte doucement et l'écran entre sur le côté (classes `assistant-*` de `globals.css`). Tout s'arrête avec `prefers-reduced-motion`.
- **Données** : 27 images WebP, 343 Ko au total. L'image suivante est préchargée, et aucune n'est chargée si le navigateur est en économie de données.
- **Source** : miniatures générées avec Figma AI (fichier « Kwa-Ba - Visuels 3D assistant hôte »). Pour en ajouter une, garder le même style : « 3D rendered miniature, soft clay style, warm light, plain solid cream background, no text ».

`espace` (`entier`, `chambre_privee`) est un nouveau champ de l'annonce : il s'affiche sur la fiche et se filtre avec `?espace=` sur `GET /api/v1/hebergements/`.
