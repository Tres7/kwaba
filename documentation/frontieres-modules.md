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
7. **Écrans d'administration.** Ils appartiennent au module : `admin_views.py` et `admin_urls.py`, branchés sur `api/v1/admin/<module>/` dans `config/urls.py`, avant `apps.backoffice.urls`. Les briques communes (`ListeAdmin`, `FicheAdmin`, `Journalise`, `ChampPhoto`) sont dans `apps.securite.backoffice`.
8. **Tests.** Comportement inchangé, plus un test qui vérifie que le nombre de requêtes d'une liste ne dépend pas du nombre d'éléments.

## Avancement

| Ordre | Module | État |
|---|---|---|
| 1 | favoris | Migré : `hebergements.api` (`est_publiee`, `cartes`), `favoris.api` (`ids_favoris`), plus de clé étrangère vers les annonces |
| 2 | experiences | Migré : écrans d'administration déplacés de `backoffice` dans le module (`admin_urls.py`) ; normalisation des photos et briques du back-office déplacées dans `securite` |
| 3 | voyages | Migré : `hebergements.api` (`resumes`, `est_disponible`), `reservations.api` (`appartient_au_voyageur`, `resumes`), `paiements.api` (`total_sejour`) ; propositions et réservations partagées gardent un identifiant au lieu d'une clé étrangère |
| 4 | concierge | Migré : `hebergements.api` (`rechercher`), `transferts.api` (`aeroports_ouverts`, `devis`), `paiements.api` (`total_sejour`) ; aucune clé étrangère à retirer |
| 5 | messaging | Migré : ses adaptateurs (`DjangoHebergementLookup`, `DjangoBookingLookup`) passent par `hebergements.api` et `reservations.api` (`paires_confirmees`, `confirmee_pour_hote`) ; le contrôleur passe par eux ; la conversation garde l'identifiant de l'annonce |
| 6 | terrain | Migré : `terrain` devient un moteur de missions générique avec un registre de types (`terrain.api.enregistrer`) ; `verifications` y déclare ses types au démarrage (`missions.py`), ce qui casse la boucle `terrain` ⇄ `verifications` |
| 7 | avis | Migré : l'avis garde les identifiants de la réservation et de l'annonce ; `reservations.api` (`sejours_termines`), `hebergements.api` (`existe`, `ids_par_nom`, `mettre_a_jour_note`) ; `avis.api` (`avis_des_reservations`, `motif_refus`), utilisé par `reservations` à la place de la relation inverse |
| 8 | verifications | Migré : le statut de vérification de l'annonce est écrit par `hebergements.api` (`enregistrer_verification`) ; la file des visites part des hôtes éligibles (identité vérifiée, `contrats.api.hotes_ayant_signe`) ; `documents.api.societe_immatriculee` ; `verifications.api` pour les autres modules ; la visite garde l'identifiant de l'annonce ; les missions de `terrain` travaillent sur des listes |
| 9 | documents | Migré : `documents` rend, numérote et sert les documents ; chaque produit (`reservations`, `transferts`, `locations`, `give`) y déclare au démarrage son bon, son reçu et ses lignes de facture (`documents.api.enregistrer`) ; le reçu de paiement passe dans `paiements` (`paiements.api.recu_pdf`) ; pagination du back-office partagée dans `securite.backoffice` |
| 9 bis | contrats | Migré : parties au contrat lues via `transferts.api`, `locations.api` et `give.api` ; taux via `paiements.api` ; société via `documents.api.societe` ; le contrat garde l'identifiant du chauffeur, du loueur ou de l'association ; `contrats.api` pour les autres modules |
| 10 | give | Migré : passe par `paiements.api`, qui expose les fonctions de paiement utilisées par les produits et les emails de paiement (`envoyer_email`, `emails_admins`, `fcfa`, `documents_joints`) ; la relation inverse `don.paiements` partira avec les clés étrangères de `PaiementModel` (étape `paiements`) |
| 11 | transferts | Migré : passe par `paiements.api` et `reservations.api` (séjour associé vérifié avec `appartient_au_voyageur`) ; le transfert garde l'identifiant du séjour |
| 12 | locations | Migré : chauffeurs lus via `transferts.api` (`fiche_chauffeur`, `fiches_chauffeurs`, `chauffeurs_actifs`, `chauffeurs_des_transferts_termines`) ; Pack Séjour via `reservations.api.reduire_frais_pack_sejour` et `paiements.api.rembourser_en_partie` ; la location et le versement au chauffeur gardent les identifiants du séjour et des chauffeurs |
| 13 | hebergements | Migré : ne lit plus les réservations ; disponibilités, calendrier de l'hôte, archivage et suppression d'un type passent par un registre que `reservations` remplit au démarrage (`hebergements/occupations.py`) ; règle de publication via `contrats.api.condition_contrat_signe` et `documents.api.condition_societe_immatriculee` ; emails d'alerte et tarif fidélité via `paiements.api` |
| 13 bis | reservations | Migré : la réservation garde les identifiants de l'annonce et du type ; création via `hebergements.api` (`fiche`, `fiche_type`, `type_par_defaut`, `verrouiller_types`, `conflit`) et `paiements.api` (`devis_sejour`, `montants_de`, `annuler_reservation`) ; carte de l'annonce lue une fois par liste (`cartes`) ; `paiements` et `backoffice` lisent l'annonce d'une réservation via `hebergements.api` |
| 14 | paiements | En cours. Fait : `paiements` ne connaît plus `give`, `transferts` ni `locations` ; chaque produit déclare au démarrage son traitement « paiement reçu », sa tâche périodique, ses versements suivis par webhook et ses relances (`paiements/registre.py`, `<produit>/paiement.py`). Reste : lectures `.paiements` / `.remboursements` des produits, clés étrangères de `PaiementModel`, `RemboursementModel` et `VersementModel`, confirmation d'un séjour dans `reservations` |
| 15 | backoffice | À faire |
| 16 | users (clés étrangères vers les comptes) | À faire |
