# Réglages du site : modules, mentions légales et mesure d'audience

Depuis l'audit n° 3 (octobre 2026), certains éléments du site se règlent dans l'environnement de l'API
(`server/.env` en local, `server.env` sur le VPS) : il suffit de modifier la variable puis de **redémarrer l'API**.
Aucun déploiement de code n'est nécessaire. Le site lit ces réglages sur `GET /api/v1/site/`.

## Interrupteurs des modules

| Variable | Module | Au lancement |
|---|---|---|
| `MODULE_EXPERIENCES` | Expériences (page Découvrir) | masqué |
| `MODULE_TOGETHER` | Voyager à plusieurs | masqué |
| `MODULE_GIVE` | Kwa-Ba Give | masqué |
| `MODULE_CONCIERGE` | Concierge IA | masqué |
| `MODULE_LOCATION_SANS_CHAUFFEUR` | Formule « Je conduis » de la location | masquée |
| `MODULE_PAIEMENTS_NON_OUVERTS` | MTN, Orange Money, Celtiis, Airtel, PayPal | masqués |

`True` affiche le module, toute autre valeur (ou l'absence de la variable) le masque.

Un module masqué :

- disparaît du menu, du menu mobile, du pied de page, du profil et du plan du site (`sitemap.xml`) ;
- a ses adresses redirigées vers l'accueil (`client/src/middleware.ts`, réglages relus au plus toutes les minutes) ;
- garde tout son code en place.

Contrôles faits aussi par l'API :

- Concierge masqué : ses adresses répondent 404 et aucune requête ne part vers Gemini (`config/site.py`,
  `apps/concierge/views.py`, test `tests/integration/site/test_site.py`) ;
- moyens non ouverts : seuls Moov Money (Flooz), Mixx by Yas (T-Money) et la carte sont proposés
  (`apps/paiements/operateurs.py`) ; les versements aux partenaires saisis dans le back-office gardent la liste complète ;
- location sans chauffeur : devis et réservation refusés (`apps/locations/services.py`).

Les expériences publiées sont limitées au Togo, sans les restaurants (`apps/experiences/views.py`), indépendamment de
l'interrupteur. Voir `documentation/modules/experiences.md`.

## Numéros légaux

| Variable | Affichée dans |
|---|---|
| `SOCIETE_RCCM` | mentions légales, CGV, confidentialité |
| `SOCIETE_NIF` | mentions légales, CGV |
| `SOCIETE_COMMERCE_ELECTRONIQUE` | mentions légales, CGV (décret n° 2018-062/PR) |
| `SOCIETE_IPDCP` | mentions légales, CGV, confidentialité |

Vides, elles s'affichent « à compléter ». Pour le RCCM et le NIF, la valeur saisie dans le back-office
(Documents → Informations société, utilisée sur les factures) est reprise tant que la variable est vide.

Écrire un commentaire **sur sa propre ligne**, jamais à la suite d'une valeur vide (`SOCIETE_NIF=   # …`) : il serait
lu comme la valeur. Une valeur qui commence par `#` compte de toute façon comme vide (`_mention` dans
`server/config/settings.py`).

Pas de numéro WhatsApp Kwa-Ba : le contact passe par la messagerie du site, le formulaire de réclamation et
l'email `ASSISTANCE_CONTACT`.

## Mesure d'audience

`GOOGLE_ANALYTICS_ID` reçoit l'identifiant de mesure Google Analytics (`G-…`, Administration → Flux de données).

- Vide ou mal formée, le site ne mesure rien et n'affiche ni bandeau de cookies ni lien « Gérer les cookies » : il n'y a
  rien à accepter.
- Renseignée, le bandeau est proposé aux visiteurs. Google n'est contacté, et ses cookies déposés, qu'après leur accord
  (`client/src/lib/mesure-audience.ts`).
- Refuser ou retirer son accord coupe l'envoi et supprime les cookies `_ga`. Le choix est redemandé après 6 mois.

Google reçoit le chemin de la page, jamais ses paramètres, et l'identifiant n'est conservé que pour les fiches publiques
(logements, projets Give) : les liens de contrat et d'invitation sont des secrets. Une nouvelle page avec un paramètre doit
rejoindre `PAGES_PRIVEES`, un test le vérifie. Le back-office et l'espace agent ne sont pas mesurés. Les fonctions
publicitaires restent coupées.

À régler dans Google Analytics :

- Administration → Conservation des données : 14 mois au plus, durée annoncée dans la politique de confidentialité ;
- Google Signals désactivé.

Ajouter un autre outil soumis à consentement : nouvelle catégorie dans `client/src/lib/consentement.ts`, avec
`VERSION_CONSENTEMENT` augmentée pour redemander le choix, et mise à jour des politiques de cookies et de confidentialité.

## Réclamations

Le formulaire du centre d'aide (`POST /api/v1/site/reclamation/`) envoie un email à `ASSISTANCE_CONTACT`
(info@kwa-ba.com) avec l'adresse du client en réponse. Rien n'est enregistré en base. Limite : 5 envois par heure ;
captcha Turnstile pour un visiteur non connecté (s'il est configuré).
