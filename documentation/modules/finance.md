# Module finance : le grand livre des mouvements

Chaque mouvement d'argent est écrit **une seule fois**, dans une table en ajout seul, avec un code de nature et ses axes d'analyse (offre, tiers, moyen de paiement, compte d'argent, période, pièce). Tous les documents financiers sont des tris de ces lignes : aucune restitution ne recalcule depuis les réservations.

- Décision d'architecture : [ADR-024](../ADR/ADR-024-module-finance-grand-livre.md).
- Référence métier : dossier DAF du référent financier (10 et 11 novembre 2026) : cahier des charges FIN-01 à FIN-17, schéma `07_Schema_base_de_donnees.sql`, référentiel des paramètres, plan de test d'audit (séries FA à FJ).
- Code : `server/apps/finance/`. Seule interface pour les autres modules : `apps/finance/api.py` (ADR-019).

## Architecture (hexagonale, comme `agenda`)

| Couche | Contenu |
| --- | --- |
| `domain/` | `entities.py` (`Ligne`, `Ecriture`, `Mouvement`, `Referentiels`, sens, états d'un mois), `rules.py` (contrôle d'une ligne, ligne inverse, mois comptable), `exceptions.py` (`MouvementRefuse`, `RestitutionRefusee`). Python pur, sans Django |
| `application/` | `ports.py` (`GrandLivre`, `Parametres`, `Restitutions`, `Alertes`, `Journal`, `TransactionManager`, `Clock`), `service.py` (`GrandLivreService`, `RestitutionService`) |
| `infrastructure/` | `persistence/models.py` (tables), `persistence/repositories.py` (écriture, idempotence, verrous consultatifs, traduction des refus de la base), `persistence/sql_restitutions.py` (vues et fonctions SQL, source unique), `persistence/restitutions.py` (leur lecture), `notifications/alertes.py` (emails par `notifications.api`), `journal.py` (journal d'audit de `securite`), `checks.py` (contrôle `finance.E001`), `clock.py`, `container.py` |
| `api.py` | fonctions simples qui délèguent aux services ; données simples en entrée et en sortie |
| `migrations/` | `0001` tables, `0002` référentiels du fichier, `0003` garde-fous (triggers). Les vues et fonctions ne sont pas dans une migration : supprimées avant chaque `migrate`, recréées après depuis `sql_restitutions.py` (`apps.py`) |

`server/.importlinter` (contrat `finance-couches`) interdit au domaine et à l'application d'importer l'infrastructure.

## Écrire une ligne

```python
from apps.finance import api as finance

finance.enregistrer([
    finance.Ligne(nature='T01', offre='COURTE_DUREE', montant=250_000, sens=finance.ENTREE, compte_argent='FEDAPAY',
                  tiers_type='hote', tiers_id=hote_id, moyen_paiement='MOOV', reservation_id=reservation.id,
                  piece_reference=reservation.reference, externe_reference=transaction_id),
    ...
], origine='paiement', par_id=None)
```

- **Dans la transaction de l'action** (FIN-01.6) : un paiement ne réussit pas sans ses lignes, ni une ligne n'existe sans son paiement. `enregistrer` écrit tout ou rien ; c'est un appel direct, pas un événement (ADR-024).
- **Montants** : entiers en F CFA, strictement positifs ; le sens porte le signe. Un montant à décimales est refusé : l'arrondi revient à celui qui calcule la ventilation (au franc, jamais au détriment du partenaire).
- **Refus** : code inconnu ou inactif, sens contraire à la nature, offre non ouverte, fonds de tiers sans tiers, caution sans réservation ni location, C03 sans motif, mois verrouillé. `MouvementRefuse` est levée et l'équipe finance est alertée.
- **Idempotence** (FIN-01.7) : une même notification reçue trois fois donne une ligne. La clé est la référence externe, la nature, le sens, le compte d'argent, le tiers et la ligne de panier. Un événement rejoué avec un autre montant n'est pas écrit et déclenche une alerte.
- **Correction** : `finance.contre_passer(id, motif=..., par_id=...)` écrit la ligne inverse, datée du jour, avec son motif. Les deux lignes restent visibles. Une ligne se corrige une fois au plus, une correction ne se corrige pas, et chaque correction va au journal d'audit (`ecriture_corrigee`).

## Modules qui écrivent : déclaration et contrôle

Chaque module qui écrit dans le grand livre se déclare au démarrage (`AppConfig.ready`) :

```python
finance.declarer_ecritures('sejours', offres={'COURTE_DUREE', 'HOTEL'}, natures={'T01', 'T02', 'R01', 'R02', 'R03'},
                           ouvert=lambda: True)
```

Si un module ouvert écrirait dans une offre ou une nature inactive, ses paiements seraient refusés. Le contrôle Django `finance.E001` le détecte à chaque `migrate`, donc à chaque déploiement, qui s'arrête ; `manage.py check --database default` le joue aussi. L'écran de contrôle le montre en invariant I14 (par exemple si une offre est désactivée au back-office pendant que son module reste ouvert).

## Alertes et journal

| Événement | Où il part |
| --- | --- |
| Mouvement refusé (FIN-01.4) | email « [Kwa-Ba Finance] Mouvement refusé par le grand livre » via `notifications.api.send_mail`, gabarit `templates/emails/finance/mouvement_refuse.txt` |
| Événement du prestataire rejoué avec un autre montant | email « Événement de paiement rejoué avec un autre montant », gabarit `evenement_rejoue.txt` |
| Correction d'une ligne | journal d'audit de `securite`, action `ecriture_corrigee` (auteur, ligne, ligne inverse, motif) |

Destinataires des emails : les administrateurs actifs qui voient la section « Finances » du back-office (`users.api.emails_admins_section('finances')` : super admins, admins sans limite, admins à qui la section est ouverte, accès non expiré). Pour que le référent financier les reçoive, lui ouvrir un compte admin limité à cette section. Les emails partent tout de suite (un refus annule en général la transaction de l'appelant) ; un échec d'envoi ne fait jamais échouer l'action. Ils ne contiennent ni montant ni nom de personne (NFF-05) ; la trace technique reste dans le journal des conteneurs (logger `apps.finance`).

## Garde-fous en base

La base refuse elle-même, quel que soit l'auteur (application, script, psql) :

- toute modification ou suppression d'une ligne du grand livre et des historiques (paramètres, correspondance comptable) ;
- une ligne dont un code est inconnu ou inactif, ou dont le sens contredit la nature ;
- une ligne inverse qui ne reprend pas la nature, l'offre, le tiers, le compte et le montant de la ligne corrigée ;
- une ligne dans un mois verrouillé, ou dont le mois comptable n'est pas celui de l'événement (sauf écriture d'inventaire, `origine='calcul'`).

`deploy/postgres/roles.sql` retire aussi `UPDATE` et `DELETE` sur ces tables au rôle `kwaba_app`. À rejouer sur chaque serveur après la première migration du module. Sans `UPDATE`, ce rôle ne peut pas non plus verrouiller une ligne (`SELECT … FOR UPDATE`) : le code ne le fait jamais.

Les vues dépendent des colonnes du grand livre, mais une migration n'a pas à s'en occuper : elles sont supprimées avant chaque `migrate` et recréées après. Pour changer une vue, on modifie `sql_restitutions.py` ; le déploiement suivant la recrée.

Concurrence : pas de verrou de ligne sur le grand livre (le rôle de l'application n'a pas `UPDATE`), mais des verrous consultatifs (`pg_advisory_xact_lock`) : deux corrections simultanées de la même ligne s'attendent, et la seconde est refusée proprement.

## Restitutions (`api.py`)

| Fonction | Contenu |
| --- | --- |
| `controle_invariants()` | I5, I8 à I13, et I14 (modules ouverts : offres et natures actives) : nombre d'anomalies, 0 = respecté |
| `peut_on_cloturer(mois)` | les six contrôles, OK ou REFUSE, et quoi faire |
| `synthese(debut, fin, axe1, axe2, familles, offres)`, `rapport(code, debut, fin)` | le moteur unique des rapports ; un rapport de plus est une ligne de `finance_rapport` |
| `du_aux_partenaires()`, `cautions_detenues()`, `soldes_comptes_argent()` | les trois soldes, jamais mélangés |
| `balance_generale(mois)`, `ecritures(mois)`, `controle_equilibre()`, `marge_par_offre(mois)` | partie double et pilotage |
| `parametre(cle)` | valeur en vigueur ; une clé inactive est une erreur |

## Exigences du cahier des charges : où on en est

| Exigence | État |
| --- | --- |
| FIN-01.1 une ligne par événement d'argent | Table et natures en place. Les paiements, arrivées, versements et remboursements y écriront à la PR suivante (FIN-03) |
| FIN-01.2 axes de chaque ligne | Fait |
| FIN-01.3 ajout seul, correction par ligne inverse | Fait, refus par la base (trigger et droits) |
| FIN-01.4 code inconnu refusé, alerte | Fait, alerte aux admins « Finances » |
| FIN-01.5 entiers, arrondi chez Kwa-Ba | Entiers : fait. L'arrondi appartient au calcul de la ventilation (FIN-03) : il arrondit au franc le plus proche, comme les neuf cas de référence |
| FIN-01.6 même transaction | Interface faite ; branchement avec FIN-03 |
| FIN-01.7 idempotence | Fait |
| FIN-02 rapprochement à trois voies | Tables du relevé et du rapprochement, règle « pas de donnée = anomalie » : faites. Connexion FedaPay, frais réels, écran : lot F2 |
| FIN-03 ventilation figée au paiement | Prochaine PR |
| FIN-04 sommes dues aux partenaires | Vue faite. Écran, échéances, alertes, gel des versements : lot F2 |
| FIN-05 registre des cautions | Vue par réservation ou location. Registre des cautions de location : lot F2 ; séjours : projet séparé |
| FIN-06 fonds de garantie | Taux à 0 ; natures G sans compte (bloquent la clôture, I12) : lot F4, après l'expert-comptable |
| FIN-07 livres comptables et export | Vues livrées (partie double, livre-journal, grand-livre, balance, contrôles). Fichier CSV et écran : lot F4 |
| FIN-08 clôture mensuelle | Refus en base dans un mois verrouillé, `peut_on_cloturer`. Verrouillage et écran : lot F4 |
| FIN-09 facturation | Lot F3 (module `documents`) |
| FIN-10 tarifs complets et historique | Paramètres chargés ; page Tarifs : avec FIN-16 |
| FIN-11 dépenses, comptes courants | Natures D et F ; écrans : lot F4 |
| FIN-12 tableau de bord | Vue du taux de frais réel ; écran : lot F4 |
| FIN-13 rôle Finance, double validation, journal | Journal des corrections : fait. Le reste après le lot F2 |
| FIN-16 référentiel unique des paramètres | Table et 95 valeurs (53 actives). Lecture par le site à la place de `ReglagesTarifsModel`, ajout par l'interface, historique écrit : PR dédiée |
| FIN-17 restitution générique | Vue pivot, axes, rapports, moteur : faits. Écran de création : lot F4 |
| Invariants | I5, I8 à I13 en base, I14 ajouté (modules ouverts et référentiel). I1 à I4, I6 et I7 se comparent aux écrans (page Finances, tableau de bord) quand ils liront le grand livre |

## Écarts par rapport au fichier SQL du 10 novembre

Le fichier a été traduit dans notre architecture : modèles Django et migrations, aucune clé étrangère vers un autre module (comptes, réservations, transferts, locations gardés en UUID), types `ENUM` remplacés par des colonnes texte contrôlées. Les noms des tables et des colonnes sont ceux du fichier. Les écarts de fond :

| Écart | Pourquoi |
| --- | --- |
| T01 à T04 et T06 à T08 acceptent les deux sens (le fichier : entrée seulement) | Le fichier écrit lui-même une sortie T01 à l'arrivée du voyageur (la commission passe au produit, cas FA-01) et au remboursement : sa propre règle les refusait. T05 et T09 restent en sortie seulement |
| Une ligne inverse échappe au sens attendu de sa nature, mais doit être le miroir exact de la ligne corrigée | Sinon aucune ligne R ou T ne pouvait être corrigée (cas FB-03) |
| Monnaie électronique (I13, contrôle 3 de clôture) et cautions (I8, contrôle 5) jugées sur le solde **cumulé** | Mois par mois, un mois qui verse ce que le précédent a encaissé paraissait créditeur, et sa clôture était refusée à tort |
| Un jour sans rapprochement compte comme une anomalie (I5, contrôle 4) | Le fichier ne comptait que les rapprochements écrits : un mois jamais rapproché se clôturait (contraire à FIN-02.7) |
| Codes inconnus refusés tout de suite par le trigger ; offre, compte d'argent, type de tiers et moyen inactifs refusés comme une nature inactive | Django déclare ses clés étrangères `DEFERRABLE` (refus reporté au commit) ; FIN-01.4 |
| Clé d'idempotence élargie au sens, au compte d'argent, au tiers et à la ligne de panier ; corrections hors clé | Un panier Évasion doit la même nature à plusieurs prestataires, un virement V01 écrit deux lignes de même référence |
| Cautions suivies par réservation **ou** par location | La caution de location de voiture est aujourd'hui la seule réelle |
| `finance_synthese` cite la colonne de l'axe (`%I`) | Une ligne de `finance_axe` est une donnée, pas du code |
| Invariant I10 ajouté à la vue de contrôle (ligne écrite dans un mois après son verrouillage) | Il figurait au cahier, pas dans la vue |
| Fonds de tiers sans tiers, caution sans réservation ni location : refusés | Compte auxiliaire (FIN-07.1), registre des cautions (FIN-05.1) |
| Rapprochement du jour : identifiant propre et unicité (jour, compte) au lieu d'une clé primaire double | Habitude de nos modèles |
| Journal des actions : celui de `securite` au lieu de `finance_journal_action` | Un seul journal d'audit, déjà en ajout seul pour l'application |
| Pas de `finance_sequence_piece` ni de `finance_prochain_numero` | Les numéros de facture viennent déjà de `documents` (`SequenceFactureModel`, verrou à chaque émission) ; le lot F3 l'étend aux autres séries |
| Pas encore de `finance_caution`, `finance_validation`, ni de `tarifs_snapshot` | Créés avec leur brique : cautions de location (F2), double validation (FIN-13), ventilation au paiement (FIN-03) |

## Décisions prises le 2026-11-13

- Le module est déployé d'abord en préprod seulement ; la production suivra sur décision. Le même manifest ira ensuite en prod (tables vides : prélancement, FedaPay en sandbox).
- Les frais FedaPay sont une charge de Kwa-Ba, jamais payés par le voyageur ni imputés aux partenaires (note 01, section 3.1) : une ligne D01 par transaction, au montant du relevé FedaPay (lot F2). Le réglage « frais à la charge du marchand » est à basculer dans le tableau de bord FedaPay.
- PayPal est retiré au lancement : pas de moyen de paiement PayPal dans le grand livre.
- La caution des séjours est un projet séparé, après la réponse de FedaPay sur l'empreinte de carte.
- Ordre : FIN-03 (ventilation au paiement), puis le lot F2, puis FIN-13.
- Location sans chauffeur : le module est fermé en production (inventaire `kwa-ba-infra`) plutôt que d'ouvrir l'offre `VOITURE_SANS`.
- Gel des versements (FIN-04.6) : un interrupteur « versements gelés » par partenaire, au back-office, journalisé.
- Petites sommes de moins de 5 000 F : pas de versement groupé le vendredi pour l'instant ; l'échéance de chaque somme est affichée.

## Paramètres à zéro, en attente de décision

`fonds_garantie_taux` (5 % ou 7 %), `double_validation_seuil`, `garantie_renforcee_beneficiaire`, `prime_verification`, `experience_commission`, `experience_apporteur_hote`, `caution_evasion_plafond`, `caution_evasion_nuits`, `pack_remise_max`. Une valeur à zéro rend la règle inerte : le module tourne, mais ne produit aucun montant pour elle.

Les natures G01 et G02 (fonds de garantie) n'ont pas de compte SYSCOHADA : une ligne G apparaîtrait dans `finance_ecritures_sans_compte` et bloquerait la clôture (I12). C'est voulu, jusqu'à l'avis de l'expert-comptable.

## Tests

- `server/tests/unit/finance/` : règles du domaine et cas d'usage avec des adaptateurs factices, sans base.
- `server/tests/integration/finance/test_schema.py` : chaque vue, fonction et trigger existe et répond ; les vues disparaissent avant un `migrate` et reviennent après ; contrôle `finance.E001` et invariant I14.
- `server/tests/integration/finance/` (PostgreSQL réelle) : série FB (immuabilité, idempotence, refus, y compris par un `INSERT`, `UPDATE` ou `DELETE` direct en base), FI-02, destinataires des alertes, journal des corrections, les neuf cas de référence du prompt développeurs au franc près, les trois soldes, la partie double du cas de référence (note 12, section 8.4), les invariants et la clôture.
