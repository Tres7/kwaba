# Module paiements

Encaissement des réservations, versements aux hôtes et remboursements.
Code : `server/apps/paiements/` (backend), `client/src/lib/paiement.ts`, `client/src/app/(main)/reservation/paiement/`, `client/src/components/hote/RevenusHote.tsx` (frontend).

## Principe

Kwa-Ba encaisse tout le paiement, le conserve jusqu'au séjour, puis reverse sa part à l'hôte.

```
Voyageur ──paie 64 800 FCFA──▶ Kwa-Ba (FedaPay ou PayPal)
                                   │  conservé jusqu'à l'arrivée + 24 h
                                   ├──▶ Hôte : 55 200 FCFA (Mobile Money, via FedaPay)
                                   └──▶ Kwa-Ba : 8 400 FCFA (avant frais des prestataires)
```

| Élément | Taux | Exemple : 3 nuits à 20 000 FCFA |
|---|---|---|
| Prix des nuits | – | 60 000 |
| Frais de service voyageur | 6 % (3 % Client fidèle) | + 3 600 → le voyageur paie **63 600** |
| Commission hôte particulier | 8 % | − 4 800 → l'hôte reçoit **55 200** |
| Commission hôtel ou résidence hôtelière | 12 % | − 7 200 |
| Programme Fondateurs (50 premiers hôtes, 6 mois) | 5 % | − 3 000 |

Grille du 18 octobre 2026 (CGV 2.4, art. 6.4). Les taux sont dans `server/apps/paiements/tarifs.py` :
- **Client fidèle** : 3 % si le voyageur a déjà séjourné (réservation confirmée et terminée) chez le même hôte (`tarifs.taux_frais`). L'annonce renvoie le taux du visiteur (`frais_voyageur`), le site l'affiche.
- **Commission** selon `ConditionsHoteModel`, réglée par l'équipe dans Back-office → Utilisateurs → Commission : catégorie (particulier, hôtel) et dates du Programme Fondateurs (limité à 50 hôtes). Sans ligne : particulier à 8 %. La catégorie choisit aussi le contrat à signer (hôte B1 ou hôtel B2).

Les montants sont **figés sur la réservation** au moment où elle est créée (`prix_nuits`, `frais_service`, `commission_hote`) : changer un taux ne modifie pas les réservations existantes. Tous les montants sont des entiers en FCFA.

## Moyens de paiement

| Moyen choisi | Prestataire | Devise | Remboursement |
|---|---|---|---|
| Mobile Money | FedaPay | FCFA | Automatique, par versement sur le compte Mobile Money que le voyageur indique à l'annulation |
| Carte Visa / Mastercard | FedaPay | FCFA | **Manuel**, depuis le tableau de bord FedaPay (statut « À traiter manuellement » dans l'admin) |
| PayPal | PayPal | EUR (1 € = 655,957 FCFA) | Automatique, sur le compte ou la carte PayPal |

Les **versements aux hôtes passent toujours par FedaPay** (Mobile Money), quel que soit le moyen utilisé par le voyageur. L'argent encaissé par PayPal arrive sur le compte PayPal : il faut approvisionner le solde FedaPay pour couvrir les versements correspondants.

Pays ouverts aux versements : Togo, Bénin, Burkina Faso, Niger, Mali (`operateurs.py`). Les codes d'opérateur (`moov_tg`, `togocel`, `mtn_open`…) sont les « modes » FedaPay : **à vérifier dans le tableau de bord FedaPay** avant la production. Un mode non activé fait échouer le versement avec le message de FedaPay (visible dans l'admin Django).

## Cycle d'une réservation

1. **Réservation** : statut `pending`, dates bloquées `PAIEMENT_EXPIRATION_MINUTES` (30 min par défaut, champ `expire_le`).
2. **Paiement** : `POST /api/v1/paiements/reservations/<id>/payer/` avec `{"moyen": "mobile_money" | "carte" | "paypal"}` → `{"url": ...}`. Le navigateur part sur la page du prestataire, puis revient sur `/reservation/paiement/<id>`.
3. **Confirmation** : le statut de la transaction est **toujours relu chez le prestataire**, jamais pris du navigateur ou du contenu du webhook. Trois déclencheurs, tous idempotents :
   - la page de retour interroge `GET .../statut/` toutes les 3 s ;
   - le webhook FedaPay `POST /api/v1/paiements/webhooks/fedapay/` ;
   - le worker, à chaque passe (il rattrape les webhooks perdus, et leur absence en local).
   Paiement réussi → réservation `confirmed` + versement `planifie` à l'arrivée + 24 h (arrivée = 14 h le jour du check-in).
4. **Relances** (`relances.py`, même principe pour les transferts et les locations) : dès la réservation, email « Payez avant HH:MM » avec le lien de paiement ; à mi-délai (15 min), rappel s'il n'a pas payé ; après l'annulation, email « Réservation annulée : paiement non reçu ». L'étape atteinte est gardée dans `relance_paiement`.
5. **Sans paiement à temps** : le worker annule la réservation (`annule_par = expiration`) et libère les dates. Un paiement qui arrive après coup confirme la réservation si les dates sont encore libres, sinon il est remboursé intégralement.
6. **Versement** : à l'échéance, le worker envoie la part de l'hôte sur son compte Mobile Money (profil saisi dans Espace hôte → Revenus). Sans profil, le versement attend, et l'hôte voit le message.

## Annulation

`DELETE /api/v1/reservations/<id>/` → `services.annuler(reservation, par='voyageur')`, renvoie `{"rembourse": montant}`.

Barème de `tarifs.bareme_voyageur` (CGV, art. 10.3 et annexe 1), selon la politique choisie par l'hôte sur l'annonce
(`HebergementModel.politique_annulation`, Modérée par défaut) :

| Politique | Remboursement intégral | 50 % des nuits retenues | Rien de remboursé |
|---|---|---|---|
| Souple | jusqu'à 24 h avant | – (moins de 24 h : 1re nuit retenue) | – |
| Modérée | jusqu'à 5 jours avant | entre 5 jours et 24 h | moins de 24 h |
| Ferme | jusqu'à 30 jours avant | entre 30 et 7 jours | moins de 7 jours |

- **Délai de réflexion** : annulée dans les 48 h suivant la réservation et au moins 7 jours avant l'arrivée → tout est remboursé, quelle que soit la politique.
- **Séjours de 28 nuits ou plus** : intégral jusqu'à 30 jours avant ; ensuite, les 30 premières nuits sont retenues.
- Les frais de service ne sont rendus qu'avec un remboursement intégral. L'hôte reçoit les nuits retenues moins la commission, au taux de la réservation.

**Remboursement Mobile Money** : FedaPay ne communique pas le numéro débité. Le remboursement est créé au statut « En attente du numéro du voyageur » ; l'API d'annulation renvoie `numero_requis: true` et le site ouvre aussitôt la fenêtre « Où recevoir votre remboursement ? » (pays, opérateur, numéro). Le voyageur peut aussi le faire plus tard depuis Mes réservations. Route : `PUT /api/v1/paiements/reservations/<id>/compte-remboursement/` avec `{pays, operateur, numero}`. Le worker envoie ensuite le remboursement.

L'annulation par l'hôte ou par Kwa-Ba (`services.annuler(r, par='hote' | 'plateforme')`) rembourse tout. Pas encore exposée dans l'API : à brancher sur le back-office.

## Worker

`python manage.py traiter_paiements` (service `paiements-worker` dans `compose.yaml`, une passe par minute ; `--once` pour une seule passe). Il :
- relit les paiements en attente des 2 dernières heures ;
- expire les réservations non payées ;
- envoie les versements dus et les remboursements, et suit leur statut ;
- envoie les emails (voir plus bas).

Après un échec chez FedaPay, le nouvel essai attend 15 min, puis 30 min, 1 h, 2 h ; au 5e échec la ligne passe en « Échoué » (versement) ou « À traiter manuellement » (remboursement) et les administrateurs sont prévenus par email.

## Emails

Envoyés par le worker (`notifications.py`, gabarits dans `templates/emails/paiements/`), jamais pendant une requête web ; un envoi raté est retenté à la passe suivante, sans doublon (champs `notifie`, et `notifie_hote` pour l'email de l'hôte).

| Événement | Destinataire |
|---|---|
| Réservation en attente : « Payez avant HH:MM » | voyageur |
| Rappel à mi-délai, puis annulation faute de paiement | voyageur |
| Paiement reçu, séjour confirmé | voyageur |
| Nouvelle réservation payée (montant et date du versement, rappel si le compte de versement manque) | hôte |
| Versement envoyé (détail de la commission) | hôte |
| Remboursement envoyé | voyageur |
| Versement échoué / remboursement à traiter | tous les utilisateurs `role = admin` |

Une seule instance suffit ; deux instances ne causent pas de double envoi (chaque ligne est réservée par une mise à jour conditionnelle).

## Configuration (`server/.env`)

```
FEDAPAY_SECRET_KEY=sk_sandbox_...      # vide = FedaPay désactivé
FEDAPAY_ENV=sandbox                    # live en production
FEDAPAY_WEBHOOK_SECRET=wh_sandbox_...  # vide = signature non vérifiée (à remplir en production)
PAYPAL_CLIENT_ID=...                   # vides = PayPal non proposé
PAYPAL_CLIENT_SECRET=...
PAYPAL_ENV=sandbox
PAIEMENT_EXPIRATION_MINUTES=30
PAIEMENT_HORS_LIGNE=False              # True seulement en développement (défaut = DJANGO_DEBUG)
BACKEND_URL=https://kwa-ba.com            # liens vers l'admin dans les alertes (défaut http://localhost:8000)
PAIEMENTS_PAUSE_EMAIL=1                  # secondes entre deux emails du worker (0 avec un vrai fournisseur d'emails)
```

Sans aucune clé :
- **en production** (`PAIEMENT_HORS_LIGNE` faux, par défaut hors `DJANGO_DEBUG`), logements, transferts et locations ne peuvent pas être réservés (`503` / message « paiement momentanément indisponible ») : rien n'est jamais confirmé sans paiement ;
- **en développement** (`PAIEMENT_HORS_LIGNE=True`), les réservations sont confirmées immédiatement, sans paiement.

Webhook à déclarer dans le tableau de bord FedaPay : `https://<domaine-api>/api/v1/paiements/webhooks/fedapay/`, événements `transaction.*` et `payout.*`. En local, FedaPay ne peut pas joindre `localhost` : la page de retour et le worker suffisent.

## Tarifs (back-office → Tarifs)

Les taux ne sont plus écrits dans le code : `paiements.ReglagesTarifsModel` (une seule ligne) garde les frais de service voyageur (6 %), les frais réduits (3 %, client fidèle et Pack Séjour), les commissions hôte particulier (8 %), hôtel ou résidence (12 %), Programme Fondateurs (5 %) et transferts (15 %). La grille des frais de ménage est dans `FraisMenageModel`. La commission de la location de véhicules reste dans « Location → Règles ».

- **Back-office → Tarifs** (`GET` et `PUT /api/v1/admin/paiements/tarifs/`, en %) : entre 0 et 30 %, frais réduits jamais au-dessus des frais normaux ; chaque changement va au journal d'audit (`tarifs_modifies`, avant et après).
- **Effet** : sur les réservations faites ensuite, les montants d'une réservation étant figés. Le site (fiche, récapitulatif, Devenir hôte, estimateur, aide), les CGV et les contrats B1 et B2 (variables `{{ tarifs.… }}`) lisent les taux en vigueur. Les CGV (art. 23.1) demandent d'annoncer une modification importante aux clients 30 jours à l'avance.
- **Lecture** : une fois par requête (`tarifs.reglages()`), au plus toutes les 30 secondes hors requête (workers), relue dès qu'un nouveau taux est enregistré.

## Finances (back-office → Finances)

`GET /api/v1/admin/paiements/finances/?debut=&fin=` (un an au plus, ce mois par défaut), et les exports `finances/csv/` (chaque mouvement, séparateur `;`, pour un tableur) et `finances/pdf/` (synthèse, encaissé par produit, rapprochement jour par jour, dû aux partenaires), inscrits au journal d'audit (`finances_exportees`).

- **Encaissé** : paiements réussis de la période. **Remboursé** : remboursements envoyés (et ceux en attente).
- **Versé et dû aux partenaires** : versements aux hôtes, chauffeurs (transferts et locations), propriétaires de véhicules et ONG, envoyés dans la période ou encore à envoyer. Chaque produit donne les siens par le registre (`ProduitPaye.versements_periode`).
- **Revenu Kwa-Ba** : frais de service et commissions des paiements encaissés (`ProduitPaye.revenu`).
- **Rapprochement** : pour chaque jour, encaissé − remboursé − versé.
- **Détail d'une réservation** (back-office → Réservations → Détail, `GET /api/v1/admin/reservations/<id>/`) : ventilation du prix figé à la réservation, prix actuel de l'annonce s'il a changé, paiements, versement à l'hôte, remboursements.

## Suivi et opérations

L'admin Django (`/admin/`) liste les paiements, versements, remboursements et profils de versement. À surveiller :
- **Remboursements « En attente du numéro du voyageur »** : le voyageur n'a pas encore indiqué son compte ; il le voit dans Mes réservations.
- **Remboursements « À traiter manuellement »** : paiements par carte, ou 5 échecs d'envoi → rembourser depuis FedaPay, puis passer la ligne à « Envoyé ».
- **Versements « Échoué »** : après 5 tentatives (numéro faux, mode non activé…) ; le message d'erreur est dans `derniere_erreur`. Corriger puis repasser à « Planifié ».
- Une annulation après le versement à l'hôte est journalisée en avertissement : à régulariser avec l'hôte.

## Tests

- `server/tests/unit/paiements/` : montants, arrondis, barème d'annulation, conversion en euros (sans base).
- `server/tests/integration/paiements/` : cycle complet sur PostgreSQL, prestataires simulés (aucun appel réseau) — confirmation, idempotence, expiration, paiement tardif, versements, remboursements Mobile Money (numéro demandé au voyageur) / carte / PayPal, nouveaux essais progressifs, emails, signature des webhooks.

Voir `documentation/ci.md` pour les lancer.

## Prérequis du compte FedaPay (testés en sandbox le 8 octobre 2026)

- **Payouts** : refusés tant que FedaPay ne les a pas activés (`403 Opération non autorisée`). Sans eux, ni versements aux hôtes ni remboursements Mobile Money automatiques.
- **Carte bancaire** : à activer, sinon la page de paiement ne propose que Mobile Money.
- **Frais FedaPay** : par défaut à la charge du payeur (ajoutés au montant affiché sur la page FedaPay) ; les basculer à la charge du marchand.
- **Nom du marchand** affiché sur la page de paiement : à renseigner (« Kwa-Ba »).
- Les pays et opérateurs proposés au voyageur sur la page FedaPay dépendent des opérateurs activés sur le compte (en sandbox : « Momo Test » et la Côte d'Ivoire).
