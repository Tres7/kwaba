from datetime import date
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework.response import Response

from apps.agenda.domain import rules
from apps.agenda.domain.entities import CANCELLED
from apps.agenda.domain.settings import BOUNDS, DEFAULT_TIMEZONE, AgendaSettings, InvalidSettings
from apps.agenda.infrastructure.container import agenda_service
from apps.securite.audit import journaliser
from apps.securite.backoffice import VueAdmin
from apps.securite.permissions import has_special_permission
from apps.users import api as users

PERMISSION = 'agenda_settings'


def _settings_json(stored) -> dict:
    author = users.compte(stored.updated_by_id) if stored.updated_by_id else None
    return {
        'values': stored.values.as_dict(),
        'defaults': AgendaSettings().as_dict(),
        'bounds': {name: {'min': low, 'max': high} for name, (low, high) in BOUNDS.items()},
        'updated_at': stored.updated_at,
        'updated_by': (author.get_full_name() or author.email) if author else None,
    }


class AgendaSettingsView(VueAdmin):
    def check_permissions(self, request):
        super().check_permissions(request)
        if not has_special_permission(request.user, PERMISSION):
            self.permission_denied(request, message="Les réglages de l'agenda ne vous sont pas ouverts.")

    def get(self, request):
        return Response(_settings_json(agenda_service().stored_settings()))

    def put(self, request):
        changes = request.data if isinstance(request.data, dict) else {}
        try:
            before, stored = agenda_service().update_settings(changes, request.user.pk)
        except InvalidSettings as exc:
            return Response({'detail': str(exc), 'errors': exc.errors}, status=400)
        after = stored.values.as_dict()
        diff = {name: {'before': value, 'after': after[name]} for name, value in before.as_dict().items()
                if after[name] != value}
        if diff:
            journaliser('agenda_settings_changed', request, utilisateur=request.user, changes=diff)
        return Response(_settings_json(stored))


def _range(start, end) -> dict:
    return {'start': start, 'end': end}


def _plan_json(plan, accounts: dict) -> dict:
    account = accounts.get(plan.agenda.agent_id)
    return {
        'id': str(plan.agenda.agent_id),
        'name': (account.get_full_name() or account.email) if account else '',
        'role': account.role if account else '',
        'cities': plan.agenda.cities,
        'max_visits': plan.max_visits,
        'visits': sum(1 for a in plan.appointments if a.status != CANCELLED),
        'windows': [_range(a, b) for a, b in plan.windows],
        'blocks': [_range(a, b) for a, b in plan.blocks],
        'appointments': [{
            'id': str(a.id), 'title': a.title, 'city': a.city, 'address': a.address, 'start': a.start, 'end': a.end,
            'status': a.status, 'origin': a.origin, 'on_the_way_at': a.on_the_way_at, 'post_check': a.post_check,
        } for a in plan.appointments],
    }


class AgentPlanningView(VueAdmin):
    def get(self, request):
        requested = request.query_params.get('day', '')
        try:
            day = date.fromisoformat(requested) if requested else timezone.localdate(timezone=ZoneInfo(DEFAULT_TIMEZONE))
        except ValueError:
            return Response({'detail': 'Date invalide.'}, status=400)
        city = ' '.join(request.query_params.get('city', '').split())
        plans = agenda_service().planning(day)
        cities = sorted({c for p in plans for c in p.agenda.cities}, key=rules.normalize_city)
        if city:
            plans = [p for p in plans if rules.covers(p.agenda, city)]
        accounts = users.comptes(p.agenda.agent_id for p in plans)
        agents = sorted((_plan_json(p, accounts) for p in plans), key=lambda a: a['name'].lower())
        return Response({'day': day, 'city': city, 'timezone': DEFAULT_TIMEZONE, 'cities': cities, 'agents': agents})
