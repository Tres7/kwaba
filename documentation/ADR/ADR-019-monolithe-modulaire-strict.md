# Titre:
Monolithe modulaire strict : interface publique par module, pas de clé étrangère entre modules

# Status:
Accepté

# Contexte :
ADR-001, ADR-003 et ADR-013 prévoyaient des modules séparés par des frontières claires. Les premiers modules (`users`, `messaging`, `notifications`) les respectent. Les modules ajoutés ensuite importent directement les modèles, les services et parfois les vues des autres, et leurs tables sont reliées par des clés étrangères.

L'audit d'architecture du 28/10/2026 (`AUDIT-ARCHITECTURE.md`) a relevé 134 imports entre modules métier, 13 paires de modules qui dépendent l'un de l'autre et 57 clés étrangères entre modules. Chaque modification devient plus risquée et aucun module ne peut évoluer seul.

Kwa-Ba va traiter de plus en plus de données clientes : pièces d'identité, téléphones, paiements. Ces données doivent rester dans le module qui en a la charge, et les autres modules ne doivent recevoir que ce dont ils ont besoin.

# Options
Option 1 : Garder le couplage actuel et seulement empêcher qu'il s'aggrave.
Option 2 : Découper tout de suite en services séparés.
Option 3 : Monolithe modulaire strict, atteint progressivement, un module à la fois.

# Décision
Nous retenons l'option 3.
- Chaque module expose une interface publique, `apps/<module>/api.py`. Les autres modules n'importent que ce fichier, jamais les modèles, services, vues ou fonctions privées d'un autre module.
- Les fonctions de `api.py` reçoivent des identifiants et renvoient des données simples (dictionnaires, dataclasses), jamais des modèles Django.
- Une table ne porte pas de clé étrangère vers la table d'un autre module : elle garde l'identifiant (`UUIDField`, même colonne `<objet>_id`).
- Les lectures de plusieurs objets d'un autre module se font en une fois (`cartes(ids)`, `get_many(ids)`), jamais en boucle.
- Quand un module doit réagir à ce qui se passe dans un autre (annonce supprimée, paiement reçu…), il réagit à un événement. Les emails passent par `EmailRequestBus` (`notifications`).
- `securite` et `notifications` forment un noyau partagé que tous les modules peuvent importer. Ce noyau n'importe aucun module métier.
- Les transactions restent possibles : tout tourne dans le même processus et la même base, donc un `transaction.atomic()` peut englober des appels à plusieurs interfaces.
- La migration se fait module par module, une PR par module (voir `documentation/frontieres-modules.md`). La CI (`server/.importlinter`) autorise les imports `apps.<module>.api` et tolère les anciens imports listés. Chaque module migré retire ses lignes de cette liste.

# Conséquences :
positives (bénéfices)
- Un module se modifie et se teste sans toucher aux autres.
- Les données de chaque module ne sortent que par son interface : moins de données exposées, et, plus tard, des droits PostgreSQL par module.
- Un module pourra devenir un service séparé si le besoin apparaît, sans réécriture.

négatifs (inconvénients)
- Les jointures entre modules sont remplacées par des appels à l'interface : un peu plus de code et de requêtes.
- La base ne garantit plus l'intégrité entre modules (CASCADE, PROTECT) : ces règles passent dans le code ou dans les réactions aux événements.
- Le travail de migration représente une quinzaine de PR.

Impacts futurs
- Tout nouveau module suit ces règles dès sa création.
- Les clés étrangères vers `users` sont traitées en dernier.
- Cette décision remplace le choix du 13/10/2026 de conserver le couplage existant.
