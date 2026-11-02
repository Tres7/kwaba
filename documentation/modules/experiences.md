# Expériences (page Découvrir)

Guide de sorties au Togo : sites touristiques, activités et loisirs. Ce n'est pas un service réservable : la fiche donne des
idées et renvoie vers les logements de la ville. Tout se gère depuis le back-office (Expériences).

## Ce qui est publié

- **Togo uniquement.** Les fiches du premier guide (Marrakech, Dakar…) restent en base mais ne sont pas affichées.
- **Pas de restaurants pour le moment.** La catégorie existe toujours au back-office, l'API publique l'exclut
  (`CATEGORIES_MASQUEES` dans `server/apps/experiences/views.py`). Pour les ouvrir : retirer la catégorie de cette liste et
  remettre l'onglet dans `TABS` (`client/src/features/experiences/Decouvrir.tsx`) avec sa traduction.
- Le contenu de départ (59 fiches) est dans la migration `0004_guide_togo.py`. Elle ne touche pas à une fiche déjà modifiée
  au back-office.

## Lieux écartés volontairement

| Lieu | Raison |
|---|---|
| Région des Savanes (Dapaong, grottes de Nok, Namoudjoga) | « Déconseillée sauf raison impérative » par France Diplomatie (état d'urgence jusqu'au 13 mars 2027, autorisation écrite du ministère des Armées pour les étrangers) |
| Parc de la Kéran | Proche de la zone rouge de Mandouri ; selon Togo Tourisme, il doit encore être reconstitué |
| Parc de Fazao-Malfakassa | Fermé aux touristes depuis la fin de la gestion privée (étude MDPI, 2026) |
| Parapente, golf, pêche au gros, ponte des tortues | Cités par Togo Tourisme, mais aucun prestataire à jour trouvé |
| Chefferie de Kparatao | Conditions de visite introuvables |

À revoir si ces conseils changent : <https://www.diplomatie.gouv.fr/fr/information-par-pays/togo/conseils-aux-voyageurs-securite>.
Les fiches du front de mer de Lomé déconseillent la promenade le soir pour la même raison (agressions signalées), et les
plages rappellent que les courants sont forts.

## Prix

Un prix n'est affiché que s'il vient d'une source datée, et il reste indicatif. Dans le doute, le champ reste vide et la
fiche n'affiche rien.

| Fiche | Prix | Source |
|---|---|---|
| Parc de Sarakawa | 6 000 FCFA + 5 000 FCFA par rotation de véhicule | Panneau d'entrée du parc |
| Marché des fétiches | Guide 3 000 FCFA, photos 2 000 FCFA, entrée libre | Ministère du Tourisme |
| Maison des esclaves | 2 000 FCFA, visite guidée incluse | Ministère du Tourisme |
| Surf, voile, kitesurf | À partir de 5 000 FCFA l'heure | Ministère du Tourisme |
| Cascade de Kpimé | ≈ 2 000 FCFA (de 1 000 à 3 000 selon les avis) | Avis de voyageurs |
| Cascade de Womé | ≈ 3 000 FCFA (de 2 500 à 3 500 selon les avis) | Avis de voyageurs |

« Gratuit » est réservé aux lieux publics en accès libre (plage de Lomé, marchés, monument, cathédrales, faille d'Alédjo).

## Photos

Les 59 photos viennent de Wikimedia Commons, sous licence libre, et ont toutes été prises au Togo. Faute de mieux, quelques
fiches montrent les environs plutôt que le lieu exact : batik (Lomé), tissage, VTT (route d'Agou), surf (plage de Lomé),
forgerons de Tcharè (marché de Tcharè), abbaye de l'Ascension (paysage de Danyi), puits des enchaînés (route des esclaves
d'Agbodrafo). Elles sont dans `client/public/experiences/`, servies par le site, pour ne pas transmettre l'adresse IP des
visiteurs à un tiers.

Les licences Creative Commons imposent de citer l'auteur et la licence : chaque carte affiche ce crédit, avec un lien vers la
page d'origine. Ne pas le retirer pour une photo qui n'est pas à Kwa-Ba. Envoyer une nouvelle photo depuis le back-office vide
le crédit de l'ancienne ; le remplir si la nouvelle n'appartient pas à Kwa-Ba.
