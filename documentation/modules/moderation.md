# Modération des messages

Insultes, propos haineux, menaces et harcèlement entre hôtes et voyageurs : détection à la saisie et à l'envoi, signalement par le destinataire, sanctions progressives après confirmation par un administrateur.

Décision : [ADR-021](../ADR/ADR-021-message-moderation.md). Complète les garde-fous de la messagerie ([messaging.md](messaging.md), [ADR-018](../ADR/ADR-018-garde-fous-anti-abus-de-la-messagerie.md)).

## Où est le code

| Partie | Emplacement |
|---|---|
| Moteur de détection (normalisation, contexte, niveaux) | `server/apps/securite/moderation.py` |
| Dictionnaires | `server/apps/securite/moderation_lexicons/*.json` |
| File admin, alertes menace, purge des extraits | `server/apps/securite/fraude.py` (table `securite_alerte_fraude`, champ `kind`) |
| Échelle de sanctions (logique pure, rejeu par date de message) | `server/apps/messaging/domain/services/SanctionLadder.py` |
| Signalements, sanctions, contestations | `server/apps/messaging/application/service/ModerationService.py` |
| Envoi modéré, suspension | `MessagingService.send_message` et `_open` |
| Rétention | `server/apps/messaging/infrastructure/persistence/moderation_retention.py`, lancée chaque heure par `relay_messaging_outbox` |
| Back-office | `server/apps/backoffice/moderation.py`, page `client/src/app/backoffice/anti-fraude` |
| Front de la messagerie | `client/src/features/messaging` (`Conversation.tsx`, `ReportDialog.tsx`, `ModerationNotice.tsx`, `moderation.ts`) |

## Mode de fonctionnement

`MODERATION_MODE` :

| Valeur | Saisie | Envoi | Trace |
|---|---|---|---|
| `off` | rien | rien | aucune |
| `observe` (défaut, y compris valeur absente ou inconnue) | bouton jamais grisé | message livré | refus simulé (`simulated`) dans la file |
| `enforce` | bouton grisé (niveau « bloquer »), avertissement (niveau « avertir ») | 422, rien n'est enregistré | refus réel (`refusal`) dans la file |

En `observe`, la route de vérification répond toujours `allow` : c'est ce qui garantit que le front ne grise jamais le bouton (test `test_observe_never_greys_the_send_button`).

Préprod en `enforce`, prod en `observe` jusqu'à la validation décrite dans l'ADR. La variable se règle dans l'environnement de l'API (dépôt d'infrastructure), sans déploiement de code.

## Moteur de détection

1. **Normalisation** (`normalize`) : accents et majuscules retirés, caractères invisibles supprimés, leet décodé dans les mots qui mélangent lettres et chiffres (`c0nnard`), lettres espacées recollées dès trois lettres isolées (`c o n`), lettres répétées réduites à une seule (`connnnard` → `conard`). Les dictionnaires passent par la même normalisation.
2. **Exceptions** retirées du texte (« mort de rire », « frapper à la porte »…).
3. **Règles** : une entrée a une catégorie (`insult`, `hate`, `threat`, `harassment`), un niveau (`block` ou `warn`) et des termes.
   - `targeted: false` : le terme suffit (« fils de pute », « je vais te tuer »).
   - `targeted: true` : le terme ne compte que visant une personne, après une cible (« tu es », « vous êtes », « espèce de »…, jusqu'à deux mots de liaison) ou avant une cible placée après (« idiot que tu es »). « La chambre est minable » passe, « tu es minable » est refusé.
4. Le niveau le plus sévère l'emporte ; toutes les catégories trouvées sont renvoyées. Le mot détecté n'est jamais renvoyé au front.

### Ajouter des termes

Éditer ou ajouter un fichier JSON dans `moderation_lexicons/` (tous les fichiers sont chargés) :

```json
{
  "targets": ["tu es", "vous êtes"],
  "suffix_targets": ["que tu es"],
  "fillers": ["un", "une", "vraiment"],
  "exceptions": ["mort de rire"],
  "entries": [
    {"category": "insult", "level": "block", "targeted": true, "terms": ["imbécile", "abruti*"]},
    {"category": "threat", "level": "block", "targeted": false, "terms": ["je (vais|veux) (te|vous) (tuer|frapper)"]}
  ]
}
```

Syntaxe des termes : `*` en fin de mot pour un préfixe (`encul*`), `(a|b)` pour des variantes d'un mot, `_` pour une variante de plusieurs mots (`(m_gonna|will)`), une variante vide pour un mot facultatif (`(moi|)`). Une variante facultative ne peut pas ouvrir le terme.

Avant d'ajouter un terme, vérifier qu'il ne bloque pas une phrase courante d'hôte ou de voyageur, en tenant compte de la réduction des lettres doublées (« salle » devient « sale », « coon » devient « con »). Le corpus de `server/tests/unit/securite/test_moderation.py` (`NORMAL_MESSAGES`) doit rester entièrement accepté : y ajouter les faux positifs relevés en prod.

## Échelle de sanctions

Alimentée uniquement par les signalements confirmés, comptés par **date du message** et rejoués à chaque confirmation (`SanctionLadder.evaluate`).

| Situation | Effet |
|---|---|
| 1er et 2e cas sur 30 jours glissants | `reminder` |
| 3e et 4e cas | `formal_warning` |
| 5e cas | `short_suspension` (24 h, à partir de la confirmation) ; le compteur repart à zéro |
| 1 cas daté après la fin de la suspension de 24 h, dans les 30 jours | `long_suspension` (7 jours) |
| 1 cas daté après la fin de la suspension de 7 jours, dans les 30 jours | `admin_decision` : email aux admins, aucune suspension automatique |
| 30 jours sans cas après la fin d'une suspension | retour au niveau 0 |

Précisions de mise en œuvre :
- un cas daté **avant** la fin de la suspension en cours (message envoyé avant, confirmé tard) est rattaché à la période déjà sanctionnée : rappel des règles, sans nouvelle escalade ;
- une suspension déjà appliquée n'est jamais réappliquée par le rejeu ; seule une contestation acceptée l'annule (`cancelled_at`) et la retire du rejeu ;
- une levée ou un raccourcissement par un admin garde la suspension dans l'historique ;
- seuils et durées : variables `MODERATION_*` ci-dessous.

## Contestation

- Une fois par sanction, sous `MODERATION_CONTEST_DAYS` jours, depuis le bandeau de la messagerie.
- La contestation ne suspend pas la sanction.
- Refusée (409) si l'admin qui l'examine a confirmé le signalement et qu'un autre admin actif existe.
- Acceptée : signalement rejeté, sanctions du signalement annulées (suspension en cours levée), rejeu.

## Alertes aux administrateurs

| Alerte | Déclencheur |
|---|---|
| Menace | dès la première menace refusée, simulée, envoyée après avertissement ou signalée ; au plus un email par utilisateur et par heure, les suivantes regroupées dans le prochain email (envoyé par la passe horaire du relais) |
| Messages refusés | 3e refus réel sur 30 jours (alerte, pas une sanction) |
| Décision à prendre | sanction `admin_decision` |
| Signalements rejetés | 3e signalement rejeté du même auteur de signalement sur 30 jours |

Toutes les entrées sont dans la file anti-fraude du back-office, filtrables par nature. Consulter un signalement est tracé (`report_viewed`), comme les confirmations, rejets, contestations, levées et la conservation prolongée.

## API

Messagerie (`/api/v1/messaging`) :

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| POST | `/conversations/{id}/messages/` | `{content, confirmed?: true}` | `422 {code: "abusive_content" \| "confirmation_required", categories}` ; `403 {code: "messaging_suspended", until}` |
| POST | `/moderation/check/` | `{content}` | `{level, categories}` (throttle `messaging_moderation_check`) |
| POST | `/conversations/{id}/false-positive/` | `{content}` | `201 {recorded}` |
| POST | `/conversations/{id}/messages/{message_id}/report/` | `{reason, details?}` | `201` créé, `200` déjà signalé, `403` son propre message |
| GET | `/moderation/status/` | — | `{suspended_until, sanctions: [...]}` |
| POST | `/moderation/sanctions/{id}/contest/` | `{text}` | `200`, `409` hors délai ou déjà contestée |

Back-office (`/api/v1/admin/anti-fraude`) : `GET reports/{id}/`, `POST reports/{id}/confirm/`, `POST reports/{id}/reject/`, `POST reports/{id}/legal-hold/ {hold}`, `GET sanctions/{id}/`, `POST sanctions/{id}/contest/ {accept, note}`, `POST sanctions/{id}/lift/ {ends_at?}`. La liste accepte `?kind=`.

## Conservation

Appliquée chaque heure par le relais (`moderation_retention.purge`). Une conservation prolongée (`legal_hold`) bloque toute suppression du signalement, de ses sanctions et de son extrait.

| Donnée | Durée | Variable |
|---|---|---|
| Extraits des refus, refus simulés, blocages contestés, signalements, contestations (file admin) | 90 jours | `MODERATION_REFUSAL_EXCERPT_RETENTION_DAYS` |
| Contexte d'un signalement rejeté | 90 jours après clôture | `MODERATION_REJECTED_REPORT_RETENTION_DAYS` |
| Ligne d'un signalement rejeté (compteur par auteur du signalement) | 12 mois | `MODERATION_REPORTER_COUNTER_RETENTION_DAYS` |
| Contexte d'un signalement confirmé, texte des contestations | 12 mois | `MODERATION_CONFIRMED_REPORT_RETENTION_DAYS` |
| Sanctions et signalements confirmés (sans contenu) | 24 mois | `MODERATION_SANCTION_RETENTION_DAYS` |

## Configuration

| Variable (défaut) | Rôle |
|---|---|
| `MODERATION_MODE` (`observe`) | `off`, `observe` ou `enforce` |
| `MODERATION_WINDOW_DAYS` (30) | Fenêtre glissante des compteurs |
| `MODERATION_WARNING_THRESHOLD` (3) | Cas avant l'avertissement formel |
| `MODERATION_SUSPENSION_THRESHOLD` (5) | Cas avant la suspension courte |
| `MODERATION_FIRST_SUSPENSION_HOURS` (24) | Durée de la suspension courte |
| `MODERATION_SECOND_SUSPENSION_DAYS` (7) | Durée de la suspension longue |
| `MODERATION_REFUSAL_ALERT_THRESHOLD` (3) | Refus réels avant l'email aux admins |
| `MODERATION_ABUSIVE_REPORTER_THRESHOLD` (3) | Signalements rejetés avant l'alerte |
| `MODERATION_CONTEST_DAYS` (14) | Délai de contestation |
| `MODERATION_CONTEXT_MESSAGES` (10), `MODERATION_CONTEXT_DAYS` (7) | Contexte figé au signalement |

## Limites connues

Ni sarcasme, ni citation, ni homoglyphes (lettres d'autres alphabets), ni langue absente des dictionnaires (éwé, mina, kabiyè, nouchi). Les messages déjà envoyés ne sont pas relus. La route de vérification permet de sonder le dictionnaire, ce que la limite de fréquence ralentit. Le signalement compense ces trous.
