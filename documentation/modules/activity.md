# Journal d'activité

Qui a fait quoi, sur quoi, quand et d'où. Décision : [ADR-025](../ADR/ADR-025-journal-d-activite.md).

## Où est le code

| Partie | Emplacement |
|---|---|
| Catalogue des actions (catégorie, niveau, libellé, cible, résumé, détails lisibles) | `server/apps/activity/domain/catalogue.py` |
| Durée de conservation | `server/apps/activity/domain/retention.py` |
| Enregistrer, rechercher, compter, purger | `server/apps/activity/application/service.py` |
| Tables `activity_entry` et `activity_hold` | `server/apps/activity/infrastructure/persistence/models.py` |
| API du back-office | `server/apps/activity/infrastructure/http/`, sous `api/v1/admin/activity/` |
| Interface pour les autres modules | `server/apps/activity/api.py` |
| Écran | `client/src/features/activity`, page `/backoffice/activity` |

## Écrire dans le journal

```python
from apps.activity import api as activity

activity.record('annonce_supprimee', request, actor=request.user, annonce_id=str(annonce.pk), annonce=annonce.name,
                motif=motif)
```

- `actor` : celui qui agit (vide pour une tâche automatique ou une commande serveur).
- `target` : `activity.Target(kind, id, label)` quand la cible n'est pas déductible des détails ; sinon le catalogue la trouve (`annonce_id`, `hebergement`, `cible_id`, `appointment`, `objet` + `id`…).
- Les détails : motif, avant/après, libellés utiles. Jamais de mot de passe, de code ni de jeton.
- Une nouvelle action s'ajoute au catalogue (catégorie, niveau, libellé). Sinon elle reste visible, avec son nom technique.

## Accès

Super admins, et admins qui ont la permission spéciale « Journal d'activité » (Utilisateurs > Droits).

## Ajout seul et conservation

- Le rôle `kwaba_app` ne peut ni modifier ni supprimer une entrée (`deploy/postgres/roles.sql`).
- `python manage.py purge_activity` supprime les entrées de plus de 12 mois, sauf celles d'un signalement sous conservation légale (`activity_hold`). Lancée chaque jour par `scripts/maintenance.sh flush-tokens`, avec les identifiants des migrations.
