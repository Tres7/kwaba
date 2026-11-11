# Titre:
Modération des messages entre hôtes et voyageurs

# Status:
Accepté

# Contexte :
La messagerie (ADR-015 à ADR-018) masque déjà les coordonnées et limite le spam, mais rien n'empêche les insultes, les propos haineux, les menaces ou le harcèlement entre hôtes et voyageurs. ADR-018 avait écarté la modération pour la V1.

Un message abusif fait fuir un hôte ou un voyageur. Une menace pose en plus un problème de sécurité que la plateforme doit connaître.

Contraintes :
- les messages sont privés : ils ne doivent pas sortir de notre infrastructure ;
- un filtre trop strict bloque des messages honnêtes (« la chambre est minable », « mort de rire ») ;
- un hôte rival ou de mauvaise foi ne doit pas pouvoir faire suspendre quelqu'un en le signalant ;
- l'équipe est petite : la charge de travail des admins doit rester bornée.

# Options
Option 1 : Classifieur externe (API de modération, LLM). Il comprend mieux le contexte, mais les messages privés sortent de notre infrastructure, avec un coût et un sous-traitant à déclarer.
Option 2 : Signalement par le destinataire seulement. Simple, mais aucun message n'est arrêté avant d'être lu.
Option 3 : Moteur de détection local, signalement par le destinataire et sanctions progressives fondées sur les signalements confirmés par un admin.

# Décision
Nous retenons l'option 3.

## Mode de fonctionnement
Variable d'environnement `MODERATION_MODE` (ADR-008) :
- `off` : aucune vérification ;
- `observe` : le message part, et on enregistre ce qui aurait été refusé (refus simulé). C'est la valeur par défaut si la variable est absente ;
- `enforce` : le message est refusé.

La préprod tourne en `enforce`. La prod reste en `observe` jusqu'à la validation décrite plus bas.

En `observe`, le front ne grise jamais le bouton et n'affiche aucun avertissement. Sinon les utilisateurs n'enverraient pas ce qui aurait été refusé, et les mesures de faux positifs seraient faussées. Cette règle est couverte par un test.

## Moteur de détection
- Normalisation du texte avant analyse : accents, majuscules, leet (`c0nnard`), lettres espacées, répétitions, caractères invisibles.
- Quatre catégories : insulte, haine, menace, harcèlement.
- Trois niveaux : bloquer, avertir (« envoyer quand même ? ») ou laisser passer.
- Le contexte compte : « tu es un imbécile » est refusé, « la chambre est minable » passe.
- Dictionnaire français et anglais au départ, extensible par ajout de données, sans changer le code.
- Le moteur vit dans `securite`, à côté de la détection des coordonnées. La messagerie l'appelle par un port, comme le `ContactGuard`.

## À la saisie et à l'envoi
- Pendant la saisie, une route de vérification limitée en fréquence permet au front de griser le bouton Envoyer, avec une explication par catégorie. Le mot détecté n'est jamais affiché.
- Si cette vérification échoue, le bouton reste utilisable.
- La vérification pendant la saisie ne laisse aucune trace et ne compte jamais comme un cas.
- Le serveur fait foi à l'envoi. En `enforce` :
  - un message du niveau « bloquer » reçoit un 422 (`abusive_content`) : rien n'est enregistré, notifié ni livré ;
  - un message du niveau « avertir » doit porter une confirmation explicite. Sans elle, le serveur répond 422 (`confirmation_required`) et le front propose « envoyer quand même ? ».
- En `observe` et `off`, aucune confirmation n'est demandée.

## Signalement par le destinataire
- Un drapeau apparaît sur chaque message reçu, avec un motif (insulte, haine, menace, harcèlement, spam, arnaque, autre) et un détail facultatif.
- L'auteur du message n'est pas prévenu. On ne peut pas signaler son propre message.
- Le signalement fonctionne quel que soit le mode.

## Ce qui alimente l'échelle de sanctions
Seuls les **signalements confirmés par un admin** comptent. Un signalement non confirmé ne sanctionne jamais personne.

Ne comptent pas :
- la détection pendant la saisie ;
- les refus à l'envoi (quelqu'un qui appuie sur Entrée avant la fin de la vérification ne doit pas être sanctionné). Ils vont dans la file admin, et un email part aux admins au 3e refus sur 30 jours glissants : c'est une alerte, pas une sanction ;
- les refus simulés (`observe`) ;
- les messages envoyés après « envoyer quand même », sauf s'ils sont ensuite signalés et confirmés.

## Échelle de sanctions
Les cas sont comptés sur 30 jours glissants. Les seuils sont des paramètres modifiables sans redéploiement de code.

| Palier | Effet |
|---|---|
| 1er et 2e cas | Rappel des règles |
| 3e cas | Avertissement formel envoyé à l'utilisateur |
| 5e cas | Messagerie suspendue 24 h |
| 1 cas dans les 30 jours après la fin de la suspension de 24 h | Messagerie suspendue 7 jours |
| 1 cas dans les 30 jours après la fin de la suspension de 7 jours | Un admin décide d'une suspension de compte, jamais automatique |

- Le compteur repart à zéro après la suspension de 24 h. Le niveau d'escalade est conservé pendant les 30 jours qui suivent la fin d'une suspension, puis retombe à zéro s'il n'y a eu aucun incident.
- C'est la date du message qui compte, pas celle de la confirmation. Comme un admin peut confirmer dans le désordre, le palier se calcule en rejouant l'historique par date de message, et non avec un compteur incrémenté.
- Le palier atteint s'applique à partir de la confirmation, jamais rétroactivement. Une suspension dont la fenêtre serait déjà passée s'applique quand même, à partir de la confirmation.
- Une confirmation tardive n'annule jamais une sanction déjà appliquée : elle ajoute un cas pour la suite.
- Un utilisateur suspendu lit ses conversations mais ne peut plus écrire. Il voit la date de fin de suspension.
- Un admin peut lever ou raccourcir toute sanction.
- Les emails de sanction ne nomment jamais l'auteur du signalement. Dans une conversation à deux, la personne sanctionnée peut le deviner : les CGU disent que l'auteur n'est pas communiqué, elles ne promettent pas l'anonymat.

## Contestation
- L'utilisateur sanctionné peut contester une sanction une fois, sous 14 jours.
- La contestation ne suspend pas la sanction.
- Elle est examinée, quand l'équipe le permet, par un autre admin que celui qui a confirmé le signalement.
- Si elle est acceptée, le signalement passe en « rejeté », le palier est recalculé par rejeu et la sanction en cours est levée.
- Un lien « ce n'est pas une insulte » permet aussi de contester un blocage à l'envoi. Ces contestations servent de source de faux positifs.

## Menaces
- Alerte immédiate aux admins dès la première menace refusée, signalée ou simulée, en dehors de tout compteur. En `observe`, le message est livré : l'email est alors le seul filet.
- Au plus un email par utilisateur et par heure. Les menaces suivantes arrivent quand même dans la file admin et sont regroupées dans l'email suivant.

## Signaleurs abusifs
- Un compteur de signalements rejetés par auteur du signalement, sans contenu, sur 12 mois glissants.
- Alerte aux admins à 3 signalements rejetés en 30 jours. Aucune sanction automatique : l'admin juge si l'auteur est un signaleur abusif.

## Suivi admin
- Refus, refus simulés, signalements, sanctions et alertes arrivent dans la file anti-fraude existante (`securite/fraude`). Chaque entrée indique si le refus est réel ou simulé.
- Pour un signalement, l'admin voit le message signalé et les 10 messages précédents de la même conversation, sur 7 jours au plus, rien de plus. Une copie figée est prise au moment du signalement.
- Chaque consultation est enregistrée dans le journal d'audit existant.
- Les entrées confirmées enrichissent le dictionnaire.

## Conservation

| Donnée | Durée |
|---|---|
| Extrait des messages refusés (environ 120 caractères, visible des seuls admins) | 90 jours |
| Signalement rejeté (copie du contexte) | 90 jours après clôture |
| Signalement confirmé (copie du contexte) | 12 mois |
| Sanction (date, catégorie, palier, sans contenu) | 24 mois |
| Menace susceptible de plainte | Conservation prolongée décidée par un admin, tracée dans l'audit |
| Compteur de signalements rejetés par auteur du signalement, sans contenu | 12 mois glissants |

On sépare le contenu des métadonnées : pour décider d'une suspension de compte, l'historique des sanctions suffit, sans garder les messages.

## Précisions de mise en œuvre
- Un cas daté avant la fin de la suspension en cours (message envoyé avant, confirmé tard) est rattaché à la période déjà sanctionnée : rappel des règles, sans nouvelle escalade.
- Le 4e cas d'une fenêtre donne de nouveau un avertissement formel. Chaque nouveau cas après le palier « décision d'un admin » relance une alerte aux admins.
- L'alerte immédiate sur les menaces part aussi pour un message envoyé après « envoyer quand même ».
- Le détail est dans `documentation/modules/moderation.md`.

## Validation avant le passage en `enforce` en prod
1. Un corpus de phrases écrit par l'équipe, avec des messages normaux d'hôtes et de voyageurs, passe sans faux positif.
2. Les associés cherchent les trous du filtre en préprod.
3. En prod, on reste en `observe` jusqu'à quelques centaines de messages (un nombre, pas une durée), puis on relit les refus simulés avant d'activer `enforce`.

# Conséquences :
positives (bénéfices)
- Les insultes évidentes sont arrêtées avant d'être lues, sans qu'aucun message ne sorte de notre infrastructure.
- Le signalement couvre ce que le filtre rate, en particulier les menaces sans mot interdit.
- Les sanctions s'appuient sur une décision humaine : un faux positif du filtre ou un signalement de mauvaise foi ne suspend personne.
- Le mode `observe` permet de mesurer les faux positifs en prod sans gêner les utilisateurs.

négatifs (inconvénients)
- Limites assumées : ni sarcasme, ni citation, ni homoglyphes, ni langue absente du dictionnaire.
- La route de vérification permet de sonder le dictionnaire pour trouver ce qui passe. La limitation de fréquence suffit.
- Les messages déjà envoyés ne sont pas relus.
- Les admins doivent traiter les signalements et les contestations : sans eux, l'échelle de sanctions ne progresse pas.
- Le dictionnaire demande un entretien continu.

Impacts futurs
- Avant le lancement : faire relire par un juriste les CGU et la politique de confidentialité, qui doivent mentionner les règles, les sanctions, l'accès des admins au contexte d'un signalement, les durées de conservation et le suivi des signalements rejetés.
- Hors première version : un classifieur maison entraîné sur les signalements confirmés, et les langues locales (éwé, mina, kabiyè, nouchi), qui demandent des locuteurs.
- Un classifieur externe (option 1) reste possible plus tard, en asynchrone et sans bloquer l'envoi, mais il demandera un nouvel ADR à cause du sous-traitant.
- Complète ADR-018, qui avait écarté la modération pour la V1.
