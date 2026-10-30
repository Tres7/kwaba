# ADR-020 : frontend organisé par modules métier

## Statut

Accepté

## Contexte

Le frontend range le code par nature (`app/`, `components/`, `lib/`). Les pages appellent directement l'API : 84 fichiers de `app/` et `components/` contiennent des appels HTTP. La règle métier d'un domaine est donc dispersée entre plusieurs pages, et un changement d'API touche des fichiers sans lien apparent.

Le backend a résolu le même problème par un monolithe modulaire migré module par module ([ADR-019](ADR-019-monolithe-modulaire-strict.md)).

## Décision

Le frontend adopte la même découpe, dans `client/src/features/<module>/`, avec les mêmes noms de modules que le backend quand ils existent.

- Un module expose une interface, `index.ts`. Les autres modules et les pages n'importent que cet index.
- Les appels HTTP d'un module sont dans `api.ts`, et les requêtes TanStack Query dans `hooks.ts`.
- `app/` reste la couche de composition : une page assemble des modules, sans appel HTTP.
- `lib/` reste la couche partagée et ne dépend d'aucun module. `components/ui` et `components/layout` restent les composants partagés.
- Tous les appels du navigateur passent par `lib/api.ts`. Seul le flux du Concierge utilise `fetch`, car axios ne lit pas un flux dans le navigateur.

Pas de renommage de `lib/` en `shared/` : le mot change, pas le rôle, et le renommage toucherait des centaines d'imports en conflit avec le travail en cours.

La migration se fait par PR, un module à la fois. Les frontières sont vérifiées par ESLint (`client/eslint.config.mjs`) : en erreur pour ce qui est déjà migré, en avertissement pour les appels restants dans `app/` et `components/`.

## Conséquences

- Le nombre d'avertissements `no-restricted-syntax` mesure ce qui reste à migrer.
- Un nouveau code d'un domaine migré ne peut plus appeler l'API depuis une page sans avertissement.
- Pendant la migration, les deux organisations coexistent.

Mode d'emploi et avancement : [frontieres-front.md](../frontieres-front.md).
