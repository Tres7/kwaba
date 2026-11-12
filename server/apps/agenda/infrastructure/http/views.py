import uuid
from datetime import date, datetime, time, timedelta

from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.agenda.domain.entities import CANCELLED, Appointment, AvailabilityException, WeeklySlot
from apps.agenda.domain.exceptions import AgendaError
from apps.agenda.domain.settings import PER_DAY_CEILING
from apps.agenda.infrastructure import ics
from apps.agenda.infrastructure.container import agenda_service, current_settings
from apps.export import api as export
from apps.securite.audit import journaliser
from apps.securite.permissions import a_acces_section
from apps.users import api as users

MAX_PERIOD_DAYS = 62


class IsAgent(IsAuthenticated):
    message = "Réservé aux agents de terrain."

    def has_permission(self, request, view):
        if not (super().has_permission(request, view) and request.user.role in ('agent', 'admin')):
            return False
        return request.user.role != 'admin' or a_acces_section(request.user, 'verifications')


class IsAdmin(IsAgent):
    message = "Réservé aux administrateurs."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


def _error(exc: AgendaError) -> Response:
    return Response({'detail': str(exc)}, status=exc.code)


def _time(value) -> time:
    return time.fromisoformat(str(value))


def _date(value) -> date:
    return date.fromisoformat(str(value))


def _hhmm(value: time | None) -> str | None:
    return value.strftime('%H:%M') if value else None


def _name(account) -> str:
    return (account.get_full_name() or account.email) if account else ''


def _agenda_json(agenda) -> dict:
    config = current_settings()
    return {
        'timezone': agenda.timezone,
        'cities': agenda.cities,
        'weekly_slots': [{'weekday': s.weekday, 'start': _hhmm(s.start), 'end': _hhmm(s.end)}
                         for s in sorted(agenda.weekly_slots, key=lambda s: (s.weekday, s.start))],
        'exceptions': [{'id': e.id, 'day': e.day, 'kind': e.kind, 'start': _hhmm(e.start), 'end': _hhmm(e.end)}
                       for e in sorted(agenda.exceptions, key=lambda e: (e.day, e.start or time.min))],
        'day_limits': [{'day': d, 'max_visits': n} for d, n in sorted(agenda.day_limits.items())],
        'rules': {
            'visit_duration_min': config.visit_minutes,
            'margin_min': config.margin_minutes,
            'max_per_day': config.max_per_day,
            'per_day_ceiling': PER_DAY_CEILING,
            'notice_h': config.notice_hours,
            'horizon_days': config.horizon_days,
        },
    }


def _appointment_json(appointment: Appointment, agents: dict | None = None, detail: bool = False) -> dict:
    data = {
        'id': str(appointment.id), 'title': appointment.title, 'city': appointment.city,
        'address': appointment.address, 'start': appointment.start, 'end': appointment.end,
        'status': appointment.status,
        'origin': appointment.origin, 'on_the_way_at': appointment.on_the_way_at,
        'listings': [{'id': t.id, 'title': t.title} for t in appointment.targets],
        'agent': None,
        'cancellation_reason': appointment.cancellation_reason if appointment.status == CANCELLED else '',
        'closing_reason': appointment.closing_reason, 'post_check': appointment.post_check,
    }
    if agents is not None:
        data['agent'] = {'id': str(appointment.agent_id), 'name': _name(agents.get(appointment.agent_id))}
    if detail:
        host = users.compte(appointment.requester_id)
        located = [t for t in appointment.targets if t.latitude is not None and t.longitude is not None]
        data.update({
            'position': {'latitude': located[0].latitude, 'longitude': located[0].longitude} if located else None,
            'host': {'name': _name(host), 'phone': host.phone or '', 'email': host.email} if host else None,
        })
    return data


def _period(request) -> tuple[datetime, datetime] | None:
    try:
        start = _date(request.query_params.get('start'))
        end = _date(request.query_params.get('end', start + timedelta(days=6)))
    except ValueError:
        return None
    if end < start or (end - start).days > MAX_PERIOD_DAYS:
        return None
    tz = agenda_service().agenda(request.user.pk).tz
    return datetime.combine(start, time.min, tzinfo=tz), datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz)


def _can_see(request, appointment: Appointment) -> bool:
    return appointment.agent_id == request.user.pk or request.user.role == 'admin'


class AvailabilityView(APIView):
    permission_classes = [IsAgent]

    def get(self, request):
        return Response(_agenda_json(agenda_service().agenda(request.user.pk)))

    def put(self, request):
        try:
            slots = [WeeklySlot(weekday=int(s['weekday']), start=_time(s['start']), end=_time(s['end']))
                     for s in request.data.get('weekly_slots', [])]
            cities = [str(c) for c in request.data.get('cities', [])]
        except (KeyError, TypeError, ValueError):
            return Response({'detail': 'Plages invalides.'}, status=400)
        try:
            agenda = agenda_service().set_week(request.user.pk, cities, slots)
        except AgendaError as exc:
            return _error(exc)
        return Response(_agenda_json(agenda))


class ExceptionsView(APIView):
    permission_classes = [IsAgent]

    def post(self, request):
        try:
            start, end = request.data.get('start'), request.data.get('end')
            exception = AvailabilityException(day=_date(request.data['day']), kind=str(request.data.get('kind', '')),
                                              start=_time(start) if start else None, end=_time(end) if end else None)
        except (KeyError, TypeError, ValueError):
            return Response({'detail': 'Date ou heures invalides.'}, status=400)
        try:
            agenda_service().add_exception(request.user.pk, exception)
        except AgendaError as exc:
            return _error(exc)
        return Response(_agenda_json(agenda_service().agenda(request.user.pk)), status=201)


class ExceptionView(APIView):
    permission_classes = [IsAgent]

    def delete(self, request, pk):
        try:
            agenda_service().delete_exception(request.user.pk, pk)
        except AgendaError as exc:
            return _error(exc)
        return Response(_agenda_json(agenda_service().agenda(request.user.pk)))


class DayLimitView(APIView):
    permission_classes = [IsAgent]

    def put(self, request, day):
        try:
            value = request.data.get('max_visits')
            max_visits = None if value in (None, '') else int(value)
            agenda = agenda_service().set_day_limit(request.user.pk, _date(day), max_visits)
        except (TypeError, ValueError):
            return Response({'detail': 'Limite invalide.'}, status=400)
        except AgendaError as exc:
            return _error(exc)
        return Response(_agenda_json(agenda))


class AppointmentsView(APIView):
    permission_classes = [IsAgent]

    def get(self, request):
        period = _period(request)
        if period is None:
            return Response({'detail': 'Période invalide.'}, status=400)
        is_admin = request.user.role == 'admin'
        agent = request.query_params.get('agent', '')
        agent_id = request.user.pk
        if is_admin and agent == 'all':
            agent_id = None
        elif is_admin and agent:
            try:
                agent_id = uuid.UUID(agent)
            except ValueError:
                return Response({'detail': 'Agent inconnu.'}, status=400)
        appointments = agenda_service().between(*period, agent_id)
        agents = users.comptes(a.agent_id for a in appointments) if is_admin else None
        return Response({'results': [_appointment_json(a, agents) for a in appointments]})


class AppointmentView(APIView):
    permission_classes = [IsAgent]

    def get(self, request, pk):
        try:
            appointment = agenda_service().get(pk)
        except AgendaError as exc:
            return _error(exc)
        if not _can_see(request, appointment):
            return Response({'detail': 'Rendez-vous introuvable.'}, status=404)
        return Response(_appointment_json(appointment, users.comptes([appointment.agent_id]), detail=True))


class OnTheWayView(APIView):
    permission_classes = [IsAgent]

    def post(self, request, pk):
        try:
            appointment = agenda_service().on_the_way(pk, request.user.pk)
        except AgendaError as exc:
            return _error(exc)
        journaliser('visit_on_the_way', request, utilisateur=request.user, appointment=str(appointment.id))
        return Response(_appointment_json(appointment))


class AppointmentIcsView(APIView):
    permission_classes = [IsAgent]

    def get(self, request, pk):
        try:
            appointment = agenda_service().get(pk)
        except AgendaError as exc:
            return _error(exc)
        if not _can_see(request, appointment):
            return Response({'detail': 'Rendez-vous introuvable.'}, status=404)
        return export.ics_response(ics.single_visit(appointment), ics.filename(appointment))


def _feed_url(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/api/proxy/v1/agenda/feed/{token}"


class FeedView(APIView):
    permission_classes = [IsAgent]

    def get(self, request):
        return Response({'url': _feed_url(agenda_service().agenda(request.user.pk).ics_token)})

    def post(self, request):
        token = agenda_service().regenerate_token(request.user.pk)
        journaliser('agenda_feed_regenerated', request, utilisateur=request.user)
        return Response({'url': _feed_url(token)})


class PublicFeedView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'agenda_feed'

    def get(self, request, token):
        found = agenda_service().feed(token)
        if found is None:
            return Response({'detail': 'Flux introuvable.'}, status=404)
        _, appointments = found
        return export.ics_response(ics.agent_feed(appointments), 'kwa-ba-agenda.ics', attachment=False)


class CoverageView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        service = agenda_service()
        coverage = service.coverage()
        agents = users.comptes(uuid.UUID(i) for row in coverage for i in row['agent_ids'])
        for row in coverage:
            row['agents'] = [{'id': i, 'name': _name(agents.get(uuid.UUID(i)))} for i in row.pop('agent_ids')]
        return Response({'cities': coverage, 'delays': service.delays()})


class AgentsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        accounts = users.comptes(users.ids_actifs(['agent', 'admin']))
        return Response({'results': sorted(
            ({'id': str(a.id), 'name': _name(a), 'role': a.role} for a in accounts.values()),
            key=lambda a: a['name'].lower())})
