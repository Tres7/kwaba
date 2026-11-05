# Référencement (SEO)

Ce que Google lit sur kwa-ba.com, et les règles à suivre quand on ajoute une page, une ville ou un pays.

## Pages par pays, ville et quartier

| Adresse | Page | Titre |
|---|---|---|
| `/tg` | Togo : ses villes et tous ses logements | Logements vérifiés au Togo |
| `/tg/lome` | Lomé : ses quartiers, ses logements, idées de sorties | Logements vérifiés à Lomé, Togo |
| `/tg/lome/tokoin` | Un quartier de Lomé | Logements vérifiés à Tokoin, Lomé |

- **En anglais** : même adresse précédée de `/en` (`/en/tg/lome`).
- **Villes et quartiers** : ceux de `client/src/lib/quartiers.ts`. C'est la même liste que les suggestions de l'assistant de l'hôte et du champ Destination.
- **Adresse d'une ville ou d'un quartier** : son nom sans accents ni espaces (`Bè Kpota` → `be-kpota`), calculé par `lib/destinations.ts`.
- **Logement rangé dans une ville** : selon la ville saisie par l'hôte, avec ou sans accents (« Lome » compte pour Lomé).
- **Logement rangé dans un quartier** : selon son adresse (champ Quartier). Le nom le plus long l'emporte : « Bè Kpota » range le logement dans Bè Kpota, pas dans Bè. Un logement n'apparaît ainsi que sur une seule page de quartier.
- **Rendu par le serveur** : les cartes des logements sont dans le HTML reçu par Google (`features/destinations/PageDestination.tsx`). Le texte d'introduction de chaque ville est dans `messages/*.json` (`destinations.villes.<ville>`).

### Indexation

- **Une page de destination n'est indexée que si elle montre au moins un logement.** Sinon elle porte `noindex, follow` et ne figure pas dans `sitemap.xml`. Google classerait une page vide en « soft 404 ».
- **Avant l'ouverture** (`PRELANCEMENT=True`), l'API ne montre aucun logement : toutes ces pages sont donc en `noindex`. Elles deviennent indexables d'elles-mêmes dès qu'un logement est publié.
- **API injoignable** : la page renvoie une erreur 500 plutôt qu'une page vide. Google revient plus tard au lieu de retirer la page.

### Ajouter une ville, un quartier ou un pays

- **Ville ou quartier** : l'ajouter dans `lib/quartiers.ts`, puis le texte d'introduction de la ville dans `messages/fr.json` et `messages/en.json` (`destinations.villes.<adresse>`).
- **Pays** (Bénin : `/bj/cotonou`) :
  - ajouter son code à `CodePays` (`lib/quartiers.ts`) et à `PAYS` (`lib/destinations.ts`) ;
  - ajouter ses villes ;
  - ajouter `destinations.pays.<code>` (nom, « au Bénin », introduction, lien du guide) ;
  - si un guide existe, le déclarer dans `GUIDES` (`features/destinations/destination.ts`).
- **Nouveaux segments d'adresse** : `/tg`, `/tg/lome` et `/tg/lome/tokoin` sont des pages publiques. Elles sont déclarées comme telles dans `lib/mesure-audience.test.ts`, que toute nouvelle page dynamique doit compléter.

## Données structurées (schema.org)

Blocs JSON-LD écrits par `lib/donnees-structurees.ts` et affichés par `components/seo/JsonLd.tsx` :

- **Fiche d'un logement publié** :
  - `LodgingBusiness`, ou `Hotel` pour une chambre d'hôtel, `Hostel` pour une auberge ;
  - nom, description, photos, ville et pays, chambres, heures d'arrivée et de départ, note si le logement a des avis ;
  - une offre (`Offer`) au prix d'une nuit **frais de service inclus**, en XOF, comme la fiche l'affiche en premier ;
  - un fil d'Ariane Accueil › Togo › Lomé › quartier › logement.
- **Pages de destination** : fil d'Ariane et liste (`ItemList`) des logements affichés.
- **Accueil** : `Organization` (nom, logo, slogan) et `WebSite`.
- **Jamais dans ces blocs** : la position exacte ni le point de repère. Le voyageur ne les reçoit qu'une fois la réservation payée.
- **Sécurité** : le caractère `<` est échappé, pour qu'un nom d'annonce ne puisse pas fermer la balise. Un bloc JSON n'est pas exécuté : la CSP ne demande pas de nonce.

Pour vérifier une page en production : [Test des résultats enrichis](https://search.google.com/test/rich-results) de Google.

## Titres, langues et aperçus de liens

- **Toute page publique** passe par `metadataPage` (`lib/seo.ts`), qui fournit :
  - le titre et la description ;
  - l'adresse canonique ;
  - les versions FR et EN (`hreflang`, avec le français en `x-default`) ;
  - l'aperçu Open Graph et Twitter.
- **Titre de l'accueil** : « Kwa-Ba · Logements vérifiés à Lomé et partout au Togo » (`meta.titreAccueil`). Le slogan reste le titre par défaut du site.
- **Fiche d'un logement** : « Nom · Villa à Lomé ». La ville est écrite avec ses accents même si l'hôte l'a tapée sans.

## sitemap.xml et robots.txt

- **`sitemap.xml`** (`app/sitemap.ts`) contient, chacun en FR et en EN :
  - les pages publiques ;
  - les pages de destination qui ont des logements ;
  - les logements publiés ;
  - les associations de Give.
- **`robots.txt`** (`app/robots.ts`) exclut les pages privées : compte, messages, paiement, back-office et API.

## Pas encore fait

- **Contenu de la fiche d'un logement** : il est rendu par le navigateur, seuls ses titre, description et données structurées viennent du serveur. Google exécute le JavaScript, mais plus lentement. Le passer en composant serveur fait partie du point A6 de l'audit d'architecture.
- **Adresse d'un logement** : elle reste `/hebergements/<id>`. Une adresse sous sa ville (`/tg/lome/<nom>`) demanderait de changer tous les liens et de rediriger les anciens.
