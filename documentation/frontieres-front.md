# Frontières du frontend

Règles : [ADR-020](ADR/ADR-020-frontend-par-modules.md). Vérification : `client/eslint.config.mjs`, lancé par `npm run lint` en CI.

```text
client/src/
  app/                   pages : importent l'écran de leur module, sans appel HTTP
  features/<module>/
    index.ts             interface du module pour le reste du code
    api.ts               appels à l'API
    hooks.ts             requêtes TanStack Query
    *.tsx                composants du module
    admin/               écrans du back-office, en français
  components/ui, layout  composants partagés
  lib/                   client HTTP, formats, utilitaires : ne dépend d'aucun module
```

Exemple complet : `client/src/features/favoris`. `client/src/features/carte` montre un module chargé à la demande : son index exporte des composants `next/dynamic`.

## Ce que vérifie ESLint

| Règle | Niveau |
| --- | --- |
| `axios` s'importe seulement dans `lib/api.ts` | erreur |
| hors de `app/`, un module s'importe par son index, jamais `@/features/x/fichier` | erreur |
| `lib/` n'importe ni `features/` ni `components/` | erreur |
| dates, prix et libellés publics par `useFormat` | erreur |
| `import api from "@/lib/api"` dans `app/` et `components/` | erreur |

## Conventions

- **Nommage** : le vocabulaire métier est en français et suit les modèles Django (`hebergement`, `reservation`, `voyageur`), le vocabulaire technique reste en anglais (`use…`, `Provider`). Le code ancien se renomme quand on y travaille, pas d'un coup.
- **Textes** : tout texte visible va dans `client/messages/fr.json` et `en.json`. Deux exceptions : le back-office et l'espace agent, qui n'existent qu'en français, gardent leurs textes dans le code ; `lib/api.ts`, hors de React, garde ses messages d'erreur réseau.
- **Tests** : un module a un `api.test.ts` pour ses chemins et ses corps, et un test à côté de chaque règle pure.
- **Clés de cache** : une seule définition par module dans `hooks.ts`. Une clé écrite deux fois fait diverger le cache sans erreur visible.

## Écrire un module

Un nouveau module suit le même chemin : une PR, sans changer ni l'affichage ni l'API.

1. **Appels.** Déplacer les appels à l'API dans `features/<module>/api.ts`, en fonctions nommées qui renvoient les données.
2. **Requêtes.** Regrouper dans `hooks.ts` les `useQuery` répétés, avec une seule clé de cache. Une même clé déclarée dans deux pages est le signe qu'un hook manque.
3. **Composants.** Déplacer les composants propres au module. Un composant utilisé par plusieurs modules reste dans `components/` ou va dans le module qui le possède, exporté par son index.
4. **Pages.** Elles importent directement leur écran (`@/features/give/ListeOrganisations`) et ne gardent que l'assemblage. L'index ne contient que ce dont les autres modules ont besoin : un composant client dans un index part avec tous ceux qui l'importent, sur toutes leurs pages.
5. **Dépendances.** Deux modules ne dépendent pas l'un de l'autre : ce qui doit les combiner va dans la page.
6. **Tests.** Un test de `api.ts` pour les chemins et les corps envoyés, plus les tests existants.
7. **Avancement.** Mettre à jour le tableau ci-dessous.

Sur la connexion, la réservation et les paiements, faire un essai complet sur un environnement de test : ce sont les parcours où une erreur coûte le plus.

## Avancement

Les 14 modules sont migrés : la règle sur les appels directs est passée en erreur.

| Ordre | Module | Périmètre | État |
|---|---|---|---|
| 1 | favoris | bouton, liste, compteur du profil | Migré |
| 2 | avis | section de la fiche, accueil, dépôt, modération | Migré |
| 3 | messaging | liste, conversation, compteur, prise de contact | Migré |
| 4 | concierge | flux compris | Migré |
| 5 | experiences | guide public et back-office | Migré |
| 6 | give | public, profil et back-office | Migré |
| 7 | voyages (Together) | liste, fiche découpée par onglet, invitation | Migré |
| 8 | verifications, agent | espace agent, pièce d'identité de l'hôte, compteurs | Migré |
| 9 | contrats, documents | signature, contrat hôte, pré-inscription, documents, factures, société | Migré |
| 10 | transferts | demande, suivi, profil et back-office | Migré |
| 11 | locations | catalogue, réservation découpée, suivi, back-office | Migré |
| 12 | hebergements | accueil, recherche, fiche, espace hôte, calendrier, types, alertes, ouverture | Migré |
| 13 | reservations, paiements | réservation, paiement, annulation, revenus, profil de versement | Migré |
| 14 | users, auth | connexion, inscription, vérification, mot de passe, profil, comptes du back-office | Migré |
