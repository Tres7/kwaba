import uuid
from datetime import date, datetime, time, timedelta

from django.utils import timezone
from rest_framework.response import Response

from apps.activity.application.ports import SearchQuery
from apps.activity.domain import catalogue
from apps.activity.domain.entities import Target
from apps.activity.infrastructure.container import activity_service
from apps.export.api import csv_response
from apps.securite.backoffice import VueAdmin
from apps.securite.limites import ip_client
from apps.securite.permissions import has_special_permission

PERMISSION = 'activity_log'
PERIODS = {'24h': timedelta(hours=24), '7d': timedelta(days=7), '30d': timedelta(days=30)}
PAGE_SIZE = 50
EXPORT_LIMIT = 10_000


class InvalidQuery(ValueError):
    pass


def _uuid(value: str):
    try:
        return uuid.UUID(value)
    except ValueError:
        raise InvalidQuery('Identifiant invalide.') from None


def _query(params, limit: int = PAGE_SIZE) -> SearchQuery:
    now = timezone.now()
    start = end = None
    if params.get('start') or params.get('end'):
        tz = timezone.get_current_timezone()
        try:
            if params.get('start'):
                start = datetime.combine(date.fromisoformat(params['start']), time.min, tzinfo=tz)
            if params.get('end'):
                end = datetime.combine(date.fromisoformat(params['end']) + timedelta(days=1), time.min, tzinfo=tz)
        except ValueError:
            raise InvalidQuery('Date invalide.') from None
    else:
        start = now - PERIODS.get(params.get('period', '7d'), PERIODS['7d'])
    actions = None
    excluded = []
    level = params.get('level', 'important')
    if level == 'sensitive':
        actions = catalogue.actions_of(levels={catalogue.SENSITIVE})
    elif level != 'all':
        excluded = catalogue.actions_of(levels={catalogue.ROUTINE})
    categories = {c for c in params.get('category', '').split(',') if c in catalogue.CATEGORIES}
    if categories:
        in_categories = catalogue.actions_of(categories=categories)
        actions = in_categories if actions is None else [a for a in actions if a in in_categories]
    before = params.get('before')
    return SearchQuery(
        text=' '.join(params.get('q', '').split())[:100],
        actor_id=_uuid(params['actor']) if params.get('actor') else None,
        ip=params.get('ip', '').strip(),
        target_kind=params.get('target_kind', ''),
        target_id=params.get('target_id', ''),
        actions=actions,
        excluded_actions=excluded,
        start=start,
        end=end,
        before_id=int(before) if before and before.isdigit() else None,
        limit=limit,
    )


def _person(person, fallback_email: str = '', role: str = '') -> dict | None:
    if person:
        return {'id': str(person.id), 'name': person.name, 'email': person.email, 'role': person.role}
    if fallback_email:
        return {'id': None, 'name': fallback_email, 'email': fallback_email, 'role': role}
    return None


def _entry_json(entry, people: dict, detail: bool = False) -> dict:
    item = catalogue.spec(entry.action)
    target = entry.target
    target_json = None
    if target:
        if target.kind == 'account':
            person = next((p for i, p in people.items() if str(i) == target.id), None)
            target = Target(target.kind, target.id, person.name if person else target.label)
        target_json = {'kind': target.kind, 'kind_label': catalogue.TARGET_KINDS.get(target.kind, target.kind),
                       'id': target.id, 'label': target.label}
    data = {
        'id': entry.id,
        'created_at': entry.created_at,
        'action': entry.action,
        'label': catalogue.label(entry.action),
        'category': item.category,
        'category_label': catalogue.CATEGORIES[item.category],
        'level': item.level,
        'summary': catalogue.summary(entry.action, entry.details, target),
        'actor': _person(people.get(entry.actor_id), entry.actor_email, entry.actor_role),
        'ip': entry.ip,
        'target': target_json,
        'legacy': entry.legacy,
    }
    if detail:
        data['details'] = catalogue.detail_lines(entry.action, entry.details)
    return data


class ActivityAdmin(VueAdmin):
    def check_permissions(self, request):
        super().check_permissions(request)
        if not has_special_permission(request.user, PERMISSION):
            self.permission_denied(request, message="Le journal d'activité ne vous est pas ouvert.")


class ActivityListView(ActivityAdmin):
    def get(self, request):
        try:
            query = _query(request.query_params)
        except InvalidQuery as exc:
            return Response({'detail': str(exc)}, status=400)
        service = activity_service()
        entries, people = service.search(query)
        return Response({
            'results': [_entry_json(e, people) for e in entries],
            'next': entries[-1].id if len(entries) == query.limit else None,
            'counts': service.counts(query),
            'today': service.today(),
            'categories': [{'code': code, 'label': label} for code, label in catalogue.CATEGORIES.items()],
        })


class ActivityDetailView(ActivityAdmin):
    def get(self, request, pk):
        entry, people = activity_service().get(pk)
        if entry is None:
            return Response({'detail': 'Événement introuvable.'}, status=404)
        return Response(_entry_json(entry, people, detail=True))


class ActivityExportView(ActivityAdmin):
    def get(self, request):
        try:
            query = _query(request.query_params, limit=EXPORT_LIMIT)
        except InvalidQuery as exc:
            return Response({'detail': str(exc)}, status=400)
        service = activity_service()
        entries, people = service.search(query)
        rows = []
        for entry in entries:
            row = _entry_json(entry, people)
            actor = row['actor'] or {}
            target = row['target'] or {}
            rows.append([
                timezone.localtime(entry.created_at).isoformat(timespec='seconds'), row['label'], row['category_label'],
                catalogue.LEVELS[row['level']], actor.get('name', ''), actor.get('email', ''), row['ip'] or '',
                f"{target.get('kind_label', '')} {target.get('label', '')}".strip(), row['summary'],
            ])
        service.record('activity_exported', actor=request.user, ip=ip_client(request),
                       details={'rows': len(entries), 'filters': dict(request.query_params.items())})
        # Names, labels and summaries come from users: csv_response writes a cell starting like a formula as text
        return csv_response(['date', 'action', 'categorie', 'niveau', 'auteur', 'email', 'ip', 'cible', 'resume'], rows,
                            f'journal-activite-{timezone.localdate()}.csv')
