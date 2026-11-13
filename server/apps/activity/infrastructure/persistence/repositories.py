from django.db.models import Count, Exists, OuterRef, Q

from apps.activity.application.ports import EntryRepository
from apps.activity.domain.entities import Entry, Target

from .models import ActivityEntryModel, ActivityHoldModel


def _entry(m: ActivityEntryModel) -> Entry:
    target = Target(kind=m.target_kind, id=m.target_id, label=m.target_label) if m.target_kind else None
    return Entry(id=m.id, action=m.action, created_at=m.created_at, actor_id=m.actor_id, actor_email=m.actor_email,
                 actor_role=m.actor_role, ip=m.ip, target=target, details=m.details or {}, legacy=m.legacy)


def _filtered(query, actor_ids):
    qs = ActivityEntryModel.objects.all()
    if query.actions is not None:
        qs = qs.filter(action__in=query.actions)
    if query.excluded_actions:
        qs = qs.exclude(action__in=query.excluded_actions)
    if query.start:
        qs = qs.filter(created_at__gte=query.start)
    if query.end:
        qs = qs.filter(created_at__lt=query.end)
    if query.actor_id:
        qs = qs.filter(actor_id=query.actor_id)
    if query.ip:
        qs = qs.filter(ip=query.ip)
    if query.target_kind:
        qs = qs.filter(target_kind=query.target_kind)
    if query.target_id:
        qs = qs.filter(target_id=query.target_id)
    if query.text:
        text = query.text
        match = (Q(actor_email__icontains=text) | Q(target_label__icontains=text) | Q(details__email__icontains=text)
                 | Q(target_id=text))
        if actor_ids:
            match |= Q(actor_id__in=actor_ids) | Q(target_kind='account', target_id__in=[str(i) for i in actor_ids])
        if all(c.isdigit() or c in '.:abcdef' for c in text.lower()) and any(c in text for c in '.:'):
            match |= Q(ip=text)
        qs = qs.filter(match)
    return qs


class DjangoEntryRepository(EntryRepository):
    def add(self, entry):
        target = entry.target
        ActivityEntryModel.objects.create(
            created_at=entry.created_at, action=entry.action, actor_id=entry.actor_id, actor_email=entry.actor_email,
            actor_role=entry.actor_role, ip=entry.ip, target_kind=target.kind if target else '',
            target_id=(target.id if target else '')[:64], target_label=(target.label if target else '')[:255],
            details=entry.details, legacy=entry.legacy)

    def search(self, query, actor_ids):
        qs = _filtered(query, actor_ids)
        if query.before_id:
            qs = qs.filter(id__lt=query.before_id)
        return [_entry(m) for m in qs.order_by('-id')[:query.limit]]

    def count_by_action(self, query, actor_ids):
        rows = _filtered(query, actor_ids).order_by().values('action').annotate(n=Count('id'))
        return {row['action']: row['n'] for row in rows}

    def get(self, entry_id):
        m = ActivityEntryModel.objects.filter(pk=entry_id).first()
        return _entry(m) if m else None

    def hold(self, target_kind, target_id, on):
        if on:
            ActivityHoldModel.objects.get_or_create(target_kind=target_kind, target_id=target_id)
        else:
            ActivityHoldModel.objects.filter(target_kind=target_kind, target_id=target_id).delete()

    def held(self, target_kind, target_id):
        return ActivityHoldModel.objects.filter(target_kind=target_kind, target_id=target_id).exists()

    def purge(self, before):
        holds = ActivityHoldModel.objects.filter(target_kind=OuterRef('target_kind'), target_id=OuterRef('target_id'))
        deleted, _ = (ActivityEntryModel.objects.filter(created_at__lt=before)
                      .annotate(held=Exists(holds)).filter(held=False).delete())
        return deleted
