from django.db import migrations

from apps.activity.domain import catalogue

TARGET_IS_ACCOUNT = {'super_admin_nomme', 'super_admin_retire', 'admin_expire'}
MISSION_KINDS = {'logement': 'listing', 'photos': 'listing', 'piece': 'account'}


def _resolve(row):
    details = row.details or {}
    actor_id, actor_email = row.actor_id, row.actor_email
    target = None
    if row.action in TARGET_IS_ACCOUNT and row.actor_id:
        target = catalogue.Target('account', str(row.actor_id), row.actor_email)
        actor_id, actor_email = None, ''
    elif row.action == 'role_modifie' and not details.get('cible_id') and row.actor_id:
        target = catalogue.Target('account', str(row.actor_id), row.actor_email)
        actor_id = details.get('agent_id') or None
        actor_email = ''
    elif row.action.startswith('mission_') and details.get('cible'):
        target = catalogue.Target(MISSION_KINDS.get(details.get('type'), 'listing'), str(details['cible']), '')
    else:
        target = catalogue.resolve_target(row.action, details)
    return actor_id, actor_email, target


def backfill(apps, schema_editor):
    Entry = apps.get_model('activity', 'ActivityEntryModel')
    batch = []
    for row in Entry.objects.all().iterator(chunk_size=500):
        actor_id, actor_email, target = _resolve(row)
        row.actor_id, row.actor_email = actor_id, actor_email
        row.target_kind = target.kind if target else ''
        row.target_id = (target.id if target else '')[:64]
        row.target_label = (target.label if target else '')[:255]
        row.legacy = row.action not in catalogue.ACTIONS and not row.action.startswith('mission_')
        batch.append(row)
        if len(batch) >= 500:
            Entry.objects.bulk_update(batch, ['actor_id', 'actor_email', 'target_kind', 'target_id', 'target_label',
                                              'legacy'])
            batch = []
    if batch:
        Entry.objects.bulk_update(batch, ['actor_id', 'actor_email', 'target_kind', 'target_id', 'target_label',
                                          'legacy'])


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0002_entry_actor_and_target'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
