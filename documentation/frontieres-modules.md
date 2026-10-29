# Frontières entre modules

Règles : [ADR-019](ADR/ADR-019-monolithe-modulaire-strict.md). Vérification : `server/.importlinter`, lancé par `lint-imports` en CI, au pre-push et par `make lint`.

## Migrer un module

Une PR par module. L'API vue par le client ne change pas.

1. **Interfaces des modules dont il dépend.** Créer ou compléter leur `api.py` avec les fonctions nécessaires : des identifiants en entrée, des données simples en sortie, des lectures groupées pour les listes.
2. **Imports.** Remplacer chaque import d'un autre module par un appel à son `api.py`.
3. **Clés étrangères.** Remplacer chaque `ForeignKey` vers un autre module par `<objet>_id = models.UUIDField(db_index=True)`. La migration s'écrit à la main pour garder la colonne et les données :
   - `AlterField` vers `ForeignKey(db_constraint=False)`, qui supprime seulement la contrainte ;
   - `SeparateDatabaseAndState` sans opération en base, qui remplace le champ dans l'état de Django (contraintes d'unicité comprises).

   Vérifier ensuite que `makemigrations --check` ne détecte rien. Contrôler aussi le SQL sur une base migrée : `sqlmigrate` doit afficher uniquement le `DROP CONSTRAINT`.
4. **Filtres qui traversent les modules** (`x__hebergement__host`, `select_related`). Les remplacer par des listes d'identifiants obtenues via l'interface.
5. **Suppressions.** Remplacer les `on_delete` entre modules : soit l'objet disparaît de l'affichage parce que l'interface ne le renvoie plus, soit le module réagit à un événement.
6. **`.importlinter`.** Retirer les lignes du module dans `ignore_imports` et vérifier que `lint-imports` passe.
7. **Tests.** Comportement inchangé, plus un test qui vérifie que le nombre de requêtes d'une liste ne dépend pas du nombre d'éléments.

## Avancement

| Ordre | Module | État |
|---|---|---|
| 1 | favoris | Migré : `hebergements.api` (`est_publiee`, `cartes`), `favoris.api` (`ids_favoris`), plus de clé étrangère vers les annonces |
| 2 | experiences | À faire |
| 3 | voyages | À faire |
| 4 | concierge | À faire |
| 5 | messaging | À faire (clé étrangère vers l'annonce, contrôleur qui contourne ses ports) |
| 6 | terrain | À faire |
| 7 | avis | À faire |
| 8 | verifications | À faire |
| 9 | documents, contrats | À faire |
| 10 | give | À faire |
| 11 | transferts | À faire |
| 12 | locations | À faire |
| 13 | reservations, hebergements | À faire |
| 14 | paiements | À faire |
| 15 | backoffice | À faire |
| 16 | users (clés étrangères vers les comptes) | À faire |
