# Correcteur de fautes des annonces

Dans les champs de texte des annonces, les fautes sont soulignées pendant la saisie : en rouge pour l'orthographe, en orange pour la grammaire. Sous le champ, chaque faute vient avec ses corrections (un appui suffit), un bouton « Ignorer » et un bouton « Tout corriger ».

C'est une aide seulement : rien n'est jamais bloqué, et l'agent ne voit pas les fautes restantes.

Code : `server/apps/correcteur/` (API) et `client/src/features/correcteur/` (champ `ChampCorrige`).

## Où il est branché

| Écran | Champs |
| --- | --- |
| Assistant de création d'annonce (`features/hebergements/assistant/Ecrans.tsx`) | titre, description, point de repère |
| Formulaire de modification (`features/hebergements/HebergementForm.tsx`) | titre, description, point de repère |

Les légendes des photos se choisissent dans une liste de pièces : il n'y a pas de texte libre à corriger. Pour brancher un autre champ, il suffit de remplacer `<input>` ou `<textarea>` par `ChampCorrige` (`multiligne` pour une zone de texte), avec `valeur` et `onValeur` à la place de `value` et `onChange`. Le champ garde ses propres classes.

## Moteur : LanguageTool sur nos serveurs

| Réglage | Valeur | Pourquoi |
| --- | --- | --- |
| Logiciel | [LanguageTool](https://languagetool.org) 6.8, image `erikvl87/languagetool` fixée par son digest | Logiciel libre, français et anglais, orthographe et grammaire |
| Réseau | `backend` (interne, sans Internet), jamais exposé | Le texte des annonces ne quitte pas le serveur |
| Mémoire | `Java_Xmx=512m`, limite du conteneur 1 Go | Mesuré le 2026-11-11 : environ 720 Mo une fois le français et l'anglais chargés. En dessous de 512 Mo de mémoire Java, Java passe son temps à libérer de la mémoire : 107 s pour une description au lieu de 0,4 s |
| Règles en mémoire | `langtool_pipelineCaching=true` | Les règles d'une langue sont chargées une fois, et non à chaque vérification (2 s → 50 ms) |
| Test de santé | une vérification en `fr`, une en `en-GB` toutes les 30 s, chacune avec une faute volontaire | Garde les deux langues chargées, avec leurs suggestions d'orthographe : aucun hôte n'attend les 8 s du premier chargement (7,5 s pour la première faute, constaté le 2026-11-11) |

À ne jamais activer : `langtool_pipelinePrewarming`. Il charge les trente langues de LanguageTool, et la mémoire Java déborde (essayé le 2026-11-11).

Temps de réponse mesurés, une fois les règles chargées : environ 35 ms pour un titre, 60 ms pour 500 caractères, 0,3 à 0,4 s pour une description de 2 000 caractères. Chaque nom propre inconnu coûte environ 0,4 s de plus la première fois. LanguageTool garde ensuite les phrases déjà vérifiées : quand l'hôte corrige un mot, seule la phrase modifiée est revérifiée (20 à 100 ms).

Piste si les premières vérifications deviennent lentes : LanguageTool lit un fichier de mots acceptés (`org/languagetool/resource/fr/hunspell/spelling_custom.txt`, idem pour `en`). Y monter `lexique.txt` lui éviterait de chercher des suggestions pour ces noms. La liste existerait alors à deux endroits (image de l'API et configuration du serveur) : ce n'est pas fait pour l'instant.

Sans LanguageTool (conteneur arrêté, en panne ou trop lent), le site marche comme avant. L'API répond `disponible: false` et le champ cesse de demander pendant 20 s. Une connexion refusée, ou trois réponses trop lentes de suite, mettent le correcteur en pause 60 s pour tout le monde : pendant ce temps, l'API répond tout de suite sans appeler LanguageTool, et les formulaires ne l'attendent pas à chaque frappe. Une seule réponse lente ne met pas le correcteur en pause : c'est souvent une description pleine de noms de lieux nouveaux, dont les suggestions prennent du temps (environ 0,4 s par nom), et LanguageTool garde le résultat pour la fois suivante. `deploy.sh` démarre le conteneur sans l'attendre : un LanguageTool qui ne démarre pas ne bloque pas un déploiement.

## API

`POST /api/v1/correcteur/verifier/` (connexion obligatoire, 600 vérifications par heure et par compte)

```json
{ "texte": "Une jolie mason", "langue": "fr" }
```

```json
{
  "disponible": true,
  "fautes": [
    { "debut": 10, "longueur": 5, "extrait": "mason", "type": "orthographe",
      "message": "Faute de frappe possible trouvée.", "remplacements": ["maison", "masson"], "regle": "FR_SPELLING_RULE" }
  ]
}
```

- Les positions sont comptées en unités UTF-16, comme dans LanguageTool (Java) et dans le navigateur (JavaScript) : un emoji compte pour deux, et le client les utilise telles quelles.
- **Langue** : chaque ligne du texte est classée en français ou en anglais d'après ses mots courants (`le`, `avec`, `the`, `with`…). Une description écrite en français puis en anglais est donc vérifiée partie par partie, chacune dans sa langue. Une ligne qui ne dit rien (« - Wifi ») suit la ligne d'avant. Sans aucun indice, c'est la langue du site (`langue`) qui compte. L'anglais est vérifié en orthographe britannique (`en-GB`), celle de l'Afrique de l'Ouest anglophone.
- 5 000 caractères au plus.

## Ce qui n'est pas signalé

- **Noms de lieux et mots locaux** (`lexique.py`). Ils viennent de deux sources :
  - `lexique.txt` : villes et quartiers proposés aux hôtes, lieux du Togo, opérateurs de paiement, mots locaux comme zémidjan ou akoumé ;
  - les villes et quartiers des annonces et les lieux des expériences, relus en base toutes les 10 minutes. Seuls les mots qui commencent par une majuscule sont pris en base, pour qu'une faute de frappe d'un hôte dans un quartier ne devienne pas un mot correct.
  
  Un nom du lexique écrit sans ses accents est corrigé : « Kpalime » devient « Kpalimé ».
- **Conseils de style** (catégorie `STYLE`), par exemple « 5 » à écrire en lettres : une annonce n'est pas une dissertation.
- **Typographie impossible au clavier d'un téléphone** : espace insécable avant « : ; ! ? », apostrophe et guillemets typographiques (`REGLES_ECARTEES` dans `services.py`).

Ces règles sont filtrées par l'API et ne sont pas envoyées à LanguageTool. Il garde en effet un jeu de règles chargé par combinaison de réglages, et celui que son test de santé garde chaud est le jeu sans réglage.

## Ordre des corrections

Pour l'orthographe, l'API reclasse les suggestions de LanguageTool (`classer_suggestions`). La plus proche de ce que l'hôte a tapé passe d'abord, accents mis à part mais majuscules comprises : pour « Deriere », LanguageTool met « D'arrière » avant « Derrière ». Une suggestion qui ajoute une apostrophe, une espace ou un trait d'union passe après les autres. À égalité, l'ordre de LanguageTool est gardé. Un nom du lexique écrit sans accents vient en tête (« Kpalime » → « Kpalimé »).

« Tout corriger » applique la première correction des fautes d'orthographe, et des fautes de grammaire qui n'en proposent qu'une (`sansChoix` dans `texte.ts`). Quand la grammaire hésite (« Les chambre » → « La chambre » ou « Les chambres »), c'est à l'hôte de choisir : la faute reste dans la liste.

## Côté navigateur

- La vérification part 900 ms après la dernière frappe (`hooks.ts`). Une réponse déjà reçue pour le même texte n'est pas redemandée.
- Pendant la frappe, les fautes de la réponse précédente restent soulignées tant que leur texte n'a pas bougé (`fautesEnPlace` dans `texte.ts`).
- Une faute ignorée l'est pour toute la visite et dans tous les champs.
- Si l'API répond que le correcteur est indisponible, le champ cesse de demander pendant 20 s.
- Le correcteur du navigateur est coupé tant que le nôtre répond : il vérifie souvent dans une autre langue que celle du texte.
- Le soulignement est un calque posé sur le champ, avec la même police, les mêmes marges et le même défilement. Il ne prend pas les clics, donc le champ reste un vrai `<textarea>` ou `<input>`.

## Charge

L'API tourne avec 2 processus Gunicorn synchrones. Une vérification en occupe un 0,05 à 0,4 s, et elle n'attend jamais LanguageTool plus de `CORRECTEUR_DELAI` (3 s). Si beaucoup d'hôtes écrivent en même temps, passer Gunicorn en `--worker-class gthread` avec plusieurs threads, comme le conseille déjà la documentation du Concierge.

## Configuration

```
CORRECTEUR_URL=http://languagetool:8010   # vide = correcteur désactivé
CORRECTEUR_DELAI=3                        # secondes d'attente au plus
```

Ces valeurs par défaut conviennent en local, en préprod et en production : rien à ajouter dans `kwa-ba-infra`.

## Tests

- `server/tests/unit/correcteur/` : langue de chaque partie du texte, positions UTF-16, ordre des suggestions.
- `server/tests/integration/correcteur/` : API, avec un faux LanguageTool. Les tests couvrent :
  - la connexion et la longueur ;
  - les fautes et les corrections ;
  - les noms togolais jamais signalés ;
  - « Kpalime » corrigé ;
  - les deux langues dans une description ;
  - les règles écartées ;
  - LanguageTool injoignable puis en pause, une réponse lente sans pause pour tous, trois de suite en pause, ou sa réponse illisible ;
  - le correcteur désactivé.
- `client/src/features/correcteur/texte.test.ts` : positions, corrections, « Tout corriger » (sans trancher à la place de l'hôte), découpage du calque.
