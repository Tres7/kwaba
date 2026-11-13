# Titre:
Module finance : grand livre des mouvements en ajout seul, garanti par la base

# Status:
Accepté

# Contexte :
Kwa-Ba encaisse l'argent des autres : sur 100 F encaissés, environ 85 ne lui appartiennent pas (hôtes, chauffeurs, propriétaires, cautions des voyageurs). Le back-office sait afficher des totaux justes (`paiements/finances.py`), mais ne garde aucune trace ligne par ligne des mouvements d'argent. Sans elle, un versement contesté ne se prouve pas, une caution oubliée ne se voit pas, et le premier bilan (dépôt au plus tard le 30 avril 2028) devrait être reconstitué à la main.

Le référent financier a remis le 10 et le 11 novembre 2026 un dossier complet : cahier des charges FIN-01 à FIN-17, schéma PostgreSQL de référence (`07_Schema_base_de_donnees.sql`), référentiel des paramètres, plan de test d'audit (séries FA à FJ). Il fixe une règle : chaque mouvement d'argent est enregistré une seule fois, avec un code de nature et ses axes d'analyse, et tous les documents financiers sont des tris de ces lignes.

Contraintes :
- monolithe modulaire strict (ADR-019) : interface `api.py`, aucune clé étrangère entre modules ;
- une ligne doit être écrite dans la même transaction que l'action qui la provoque (FIN-01.6) : un paiement ne réussit pas sans sa ligne ;
- le refus d'une modification ou d'une suppression doit venir de la base, pas seulement de l'application (critère de FIN-01) ;
- le même manifest est déployé en préprod puis en prod, et les migrations s'appliquent au déploiement ;
- aucune valeur métier en dur : taux, plafonds, délais et comptes comptables sont des données.

# Options
Option 1 : Étendre `paiements` (registre `ProduitPaye`, page Finances). Le module grossit encore, mélange l'encaissement et la comptabilité, et rien ne garantit en base que l'historique reste intact.
Option 2 : Jouer le fichier SQL tel quel, hors des migrations Django. Fidèle au fichier, mais il vise des tables `users(id)` et `reservations(id)` qui ne sont pas les nôtres, échappe à l'état des migrations et ne serait pas rejoué par le déploiement.
Option 3 : Un module `finance` hexagonal (comme `agenda` et `messaging`), le schéma traduit en modèles et migrations Django, avec les noms du fichier, et ses garde-fous, vues et fonctions en SQL dans ces migrations.

# Décision
Nous retenons l'option 3.

## Structure
- `domain/` : entités (`Ligne`, `Ecriture`, `Mouvement`, référentiels), règles pures du grand livre (contrôle d'une ligne, ligne inverse, mois comptable), exceptions (`MouvementRefuse`, `RestitutionRefusee`). Aucun import de Django.
- `application/` : ports (`GrandLivre`, `Parametres`, `Restitutions`, `Alertes`, `Journal`, `TransactionManager`, `Clock`) et cas d'usage (`GrandLivreService` : enregistrer, contre-passer, lire un paramètre ; `RestitutionService` : invariants, clôture, rapports, soldes).
- `infrastructure/` : modèles et dépôts Django (`persistence/`), vues et fonctions SQL (`persistence/sql_restitutions.py`) et leur lecture (`persistence/restitutions.py`), alertes par `notifications.api` (`notifications/alertes.py`), journal d'audit par `securite` (`journal.py`), contrôle Django (`checks.py`), `container.py`.
- `api.py` : seule porte d'entrée des autres modules ; données simples en entrée et en sortie.
- Un contrat `layers` d'import-linter (`server/.importlinter`) interdit au domaine et à l'application d'importer l'infrastructure.

## Le grand livre
- Une table `finance_mouvement` en ajout seul : montant entier positif en F CFA, sens (entrée ou sortie), nature, offre, tiers, moyen de paiement, compte d'argent, pièce, référence du prestataire, devise, champ libre `metadonnees`. Les identifiants des autres modules (réservation, transfert, location, comptes) sont gardés en UUID, sans clé étrangère.
- Les énumérations métier sont des tables (familles, natures, offres, types de tiers, comptes d'argent, moyens de paiement, axes, rapports), chargées par une migration depuis les `INSERT` du fichier. Les offres non ouvertes existent, inactives : ouvrir une offre, c'est activer des lignes.
- Les paramètres pilotables (95) sont dans `finance_parametre`, avec un historique en ajout seul.

## Garanties en base
- Triggers PostgreSQL : refus de tout `UPDATE` ou `DELETE` sur le grand livre et les historiques ; à l'insertion, refus d'un code inconnu ou inactif, d'un sens contraire à la nature, d'une ligne dans un mois verrouillé, d'une ligne inverse qui ne reprend pas exactement la ligne corrigée.
- `deploy/postgres/roles.sql` retire aussi `UPDATE` et `DELETE` au rôle de l'application sur ces tables.
- Idempotence par un index unique partiel : un même événement du prestataire n'écrit qu'une ligne par nature, sens, compte, tiers et ligne de panier.
- Les restitutions sont des vues et des fonctions SQL : partie double (deux lignes par mouvement, AUDCIF art. 17-2), livres de l'article 19, invariants, `finance_peut_on_cloturer`, moteur de rapports `finance_synthese`. Aucune ne recalcule depuis les réservations.
- Ces vues et fonctions ont une source unique, `sql_restitutions.py`, et ne sont dans aucune migration : elles sont supprimées avant chaque `migrate` (`pre_migrate`) et recréées après (`post_migrate`). Une migration peut donc changer une colonne du grand livre sans s'occuper des vues, et la base a toujours celles du code en service. Les triggers, eux, sont dans une migration : ils protègent les tables dès leur création.
- Les accès concurrents se règlent par des index uniques et par des verrous consultatifs PostgreSQL (`pg_advisory_xact_lock`), qui ne demandent aucun droit sur la table : le rôle de l'application, privé d'`UPDATE` sur le grand livre, ne peut pas y poser de verrou de ligne.

## Liens avec les autres modules
- Chaque module qui écrit déclare au démarrage les offres et les natures qu'il utilise et son interrupteur (`finance.api.declarer_ecritures`). Le contrôle Django `finance.E001`, joué par chaque `migrate` donc par chaque déploiement, arrête le déploiement si un module ouvert écrirait dans une offre ou une nature inactive ; l'écran de contrôle le montre aussi (invariant I14).
- Les modules qui déplacent de l'argent appellent `finance.api.enregistrer` **dans leur propre transaction**. C'est un appel direct et non une réaction à un événement (ADR-019, ADR-011) : un événement traité après la validation pourrait manquer, alors qu'une ligne non écrite au moment du paiement est définitivement perdue.
- Alertes : un mouvement refusé, ou un événement du prestataire rejoué avec un autre montant, part par email via `notifications.api.send_mail` aux administrateurs qui voient la section « Finances » du back-office (`users.api.emails_admins_section`). L'email part tout de suite, pas après la validation : un refus annule en général la transaction de l'appelant. Jamais de montant ni de nom de personne (NFF-05).
- Journal : chaque correction (ligne inverse) va au journal d'audit de `securite` (`ecriture_corrigee`), en ajout seul pour l'application.
- Le module ne lit aucune table d'un autre module ; `users.api` lui donne les destinataires des alertes.

## Écarts assumés par rapport au fichier SQL
Le fichier contredisait le cahier des charges sur quelques points, révélés en exécutant ses cas : sens des natures T, correction des lignes R et T, soldes jugés mois par mois au lieu du cumul, jour sans rapprochement compté comme bon, clé d'idempotence trop étroite. La liste complète et ses raisons sont dans `documentation/modules/finance.md`. Toute évolution du schéma se fait par une nouvelle migration, en ajout seul.

# Conséquences :
positives (bénéfices)
- Une seule source pour la page Finances, les relevés, l'export comptable et le bilan : s'ils divergent, c'est un bogue, pas un débat.
- La base protège l'historique, même contre un script ou un administrateur.
- Ajouter une offre, un rapport, un axe ou un paramètre est une donnée, pas un développement.
- Le domaine se teste sans base, avec des adaptateurs factices.

négatifs (inconvénients), et ce qui les limite
- Une partie de la logique vit en SQL (triggers, vues, fonctions) : elle se lit dans deux fichiers (`0003_garde_fous.py`, `sql_restitutions.py`), et des tests sur PostgreSQL vérifient à chaque CI que chaque vue, fonction et trigger existe et répond, en plus des cas métier.
- Les vues sont supprimées pendant un `migrate` : pendant les quelques secondes d'un déploiement, une restitution du back-office peut échouer. L'écriture dans le grand livre, elle, ne lit aucune vue. Si un `migrate` échoue, les vues reviennent au `migrate` suivant.
- Un mouvement refusé fait échouer l'action qui le demandait (un paiement, par exemple). C'est voulu (FIN-01.6) ; le contrôle `finance.E001` empêche de déployer un module ouvert dont le référentiel n'est pas prêt, et l'invariant I14 signale une offre désactivée après coup.
- Le domaine ne connaît pas les produits : chaque module qui écrit doit se déclarer (`declarer_ecritures`), sinon le contrôle ne le voit pas.

Impacts futurs
- Les paiements, l'arrivée du voyageur, les versements et les remboursements écriront leurs lignes (FIN-03), puis le rapprochement FedaPay, les sommes dues et les cautions (lot F2) s'appuieront sur ces lignes.
- Le rôle Finance, la double validation et le journal des actions sensibles (FIN-13) réutiliseront les ports `Journal` et `Alertes`.
- Les numéros de pièce restent dans `documents` (`SequenceFactureModel`), étendu aux autres séries au lot F3.
