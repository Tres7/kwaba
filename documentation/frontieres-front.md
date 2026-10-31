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
| `import api from "@/lib/api"` dans `app/` et `components/` | avertissement, à retirer module par module |

## Migrer un module

Une PR par module. L'affichage et l'API ne changent pas.

1. **Appels.** Déplacer les appels à l'API dans `features/<module>/api.ts`, en fonctions nommées qui renvoient les données.
2. **Requêtes.** Regrouper dans `hooks.ts` les `useQuery` répétés, avec une seule clé de cache. Une même clé déclarée dans deux pages est le signe qu'un hook manque.
3. **Composants.** Déplacer les composants propres au module. Un composant utilisé par plusieurs modules reste dans `components/` ou va dans le module qui le possède, exporté par son index.
4. **Pages.** Elles importent directement leur écran (`@/features/give/ListeOrganisations`) et ne gardent que l'assemblage. L'index ne contient que ce dont les autres modules ont besoin : un composant client dans un index part avec tous ceux qui l'importent, sur toutes leurs pages.
5. **Dépendances.** Deux modules ne dépendent pas l'un de l'autre : ce qui doit les combiner va dans la page.
6. **Tests.** Un test de `api.ts` pour les chemins et les corps envoyés, plus les tests existants.
7. **Avancement.** Mettre à jour le tableau ci-dessous.

Les paiements, la réservation et la connexion passent en dernier, avec un essai complet sur un environnement de test : ce sont les parcours où une erreur coûte le plus.

## Avancement

Fichiers avec un appel direct à l'API : `npm run lint`, règle `no-restricted-syntax`.

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
| 13 | reservations, paiements | | À faire |
| 14 | users, auth | | À faire |
