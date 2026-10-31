# Carte des logements

La recherche affiche les logements sur une carte, avec leur prix. La fiche d'un logement montre une zone, jamais son emplacement exact.
Code : `client/src/features/carte/` (carte), `server/apps/hebergements/positions.py` (position publique).

## Position d'un logement

- L'hôte la place sur la carte dans le formulaire d'annonce, en touchant la carte ou avec **Utiliser ma position**. Elle est obligatoire pour une nouvelle annonce (`400` sinon).
- Une annonce créée avant la carte reste modifiable sans position. Elle n'apparaît pas sur la carte, et la recherche indique combien de logements manquent.
- Déplacer le repère d'une annonce vérifiée la remet en vérification. Une première position sur une annonce ancienne ne le fait pas : rien de ce que l'agent a vu n'a bougé.

## Position exacte et position publique

La position exacte mènerait à l'hôte sans réservation : elle n'est jamais envoyée aux voyageurs.

| Qui | Champs de l'API |
|---|---|
| L'hôte de l'annonce | `latitude`, `longitude` et `position` |
| Agents et administrateurs, dans la file des visites | `position`, ici exacte, pour le bouton **Itinéraire** |
| Tous les autres, et la fiche publique pour tout le monde | `position` approchée |

`position` vaut `{lat, lng, rayon_m}` : un point à 150 à 400 m de l'emplacement réel, qui reste donc dans le cercle de rayon `rayon_m` dessiné sur la fiche. Le décalage vient de l'identifiant de l'annonce et de `DJANGO_SECRET_KEY` : il ne change pas d'une requête à l'autre, et comparer les réponses n'apprend rien. Changer cette clé déplace légèrement tous les points publics.

## Recherche

- Le bouton **Carte** affiche la liste et la carte côte à côte sur ordinateur, et la carte en plein écran sur téléphone. Les filtres passent alors dans le panneau **Filtres**.
- Le prix affiché est celui des cartes de la liste : prix de la nuit, frais de service inclus, dans la devise choisie.
- Les prix qui se chevaucheraient sont regroupés (« 6 logements ») : toucher le groupe zoome dessus. À partir du zoom 15, chaque logement a son prix.
- Survoler un logement de la liste met son prix en avant. Toucher un prix ouvre un aperçu du logement.
- Avec des dates, un logement complet garde son prix, en gris.

## Vue 3D

Le bouton **3D** incline et tourne la carte, sur la recherche et la fiche d'un logement. Il garde le zoom du visiteur : les bâtiments se dressent à partir du zoom 14 et, plus loin, on voit la ville en perspective.

- La caméra est celle de la démo d'OpenFreeMap : 60° d'inclinaison, 55° d'orientation (`BoutonRelief.tsx`). Les bâtiments sont la couche `building-3d` du style (`COUCHE_RELIEF`, `features/carte/style.ts`) : le bouton ne charge aucun autre style.
- La fiche s'ouvre en 3D sur grand écran. Sur téléphone, le visiteur choisit : en vue inclinée, il voit plus loin et charge environ 3 fois plus de tuiles (1,5 Mo contre 430 Ko à Lomé, mesuré au zoom 15).
- La carte où l'hôte place son logement reste à plat : la précision compte plus que le relief.
- Beaucoup de bâtiments du Togo n'ont pas de hauteur renseignée dans OpenStreetMap : ils s'affichent bas, et les plus connus ont leur vraie hauteur.

## Fond de carte

MapLibre GL dessine la carte à partir des tuiles d'[OpenFreeMap](https://openfreemap.org), issues d'OpenStreetMap : pas de clé, pas de limite, pas de cookie. Toutes les cartes utilisent le style `liberty` tel quel, en couleurs : mer bleue, routes jaunes, verdure, noms des quartiers (`features/carte/style.ts`).

- **Sans garantie de service** : OpenFreeMap est gratuit. S'il ne répond pas, un message remplace la carte au bout de 15 secondes et la liste reste utilisable. Les prix s'affichent dès que le style est reçu : une tuile lente ne les retarde pas. Changer de fournisseur : `STYLE_CARTE` dans `style.ts` et `connect-src` dans `client/src/lib/csp.ts`.
- **Crédits** : MapLibre affiche ceux d'OpenStreetMap et d'OpenMapTiles sur chaque carte. Ils sont obligatoires, il ne faut pas les masquer.
- **Poids** : MapLibre n'est chargé que sur les pages qui montrent une carte (`features/carte/chargeurs.tsx`).
- **CSP** : MapLibre 6 dessine dans un worker. Webpack le publie avec le site, d'où `worker-src 'self'`.
- **Confidentialité** : OpenFreeMap reçoit l'adresse IP des visiteurs et ne dépose aucun cookie : la carte ne demande pas d'accord.
