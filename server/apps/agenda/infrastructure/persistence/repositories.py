import hashlib
from typing import ContextManager

from django.db import IntegrityError, connection, transaction

from apps.agenda.application.ports import (
    AgendaRepository, AppointmentRepository, DigestRepository, TransactionManager,
)
from apps.agenda.domain.entities import (
    CONFIRMED, DONE, Agenda, Appointment, AvailabilityException, Target, WeeklySlot,
)
from apps.agenda.domain.exceptions import SlotUnavailable

from .models import (
    AgendaModel, AppointmentModel, AvailabilityExceptionModel, DayLimitModel, DigestModel, WeeklySlotModel, new_token,
)

ACTIVE = [CONFIRMED, DONE]
NO_OVERLAP = 'agenda_appointment_no_overlap'


class DjangoTransactionManager(TransactionManager):
    def atomic(self) -> ContextManager:
        return transaction.atomic()


def _agenda(m: AgendaModel) -> Agenda:
    return Agenda(
        id=m.id, agent_id=m.agent_id, timezone=m.timezone, cities=list(m.cities or []),
        weekly_slots=[WeeklySlot(weekday=s.weekday, start=s.start, end=s.end) for s in m.weekly_slots.all()],
        exceptions=[AvailabilityException(id=e.id, day=e.day, kind=e.kind, start=e.start, end=e.end)
                    for e in m.exceptions.all()],
        day_limits={limit.day: limit.max_visits for limit in m.day_limits.all()},
        ics_token=m.ics_token, availability_reminder_at=m.availability_reminder_at,
    )


def _with_details(qs):
    return qs.prefetch_related('weekly_slots', 'exceptions', 'day_limits')


class DjangoAgendaRepository(AgendaRepository):
    def for_agent(self, agent_id):
        m = _with_details(AgendaModel.objects.filter(agent_id=agent_id)).first()
        return _agenda(m) if m else None

    def create(self, agent_id):
        m, _ = AgendaModel.objects.get_or_create(agent_id=agent_id)
        return _agenda(m)

    def lock(self, agenda_ids):
        list(AgendaModel.objects.select_for_update().filter(pk__in=agenda_ids).order_by('pk').values_list('pk'))

    def all(self):
        return [_agenda(m) for m in _with_details(AgendaModel.objects.order_by('agent_id'))]

    def for_token(self, token):
        m = _with_details(AgendaModel.objects.filter(ics_token=token)).first()
        return _agenda(m) if m else None

    def save_week(self, agenda, cities, slots):
        AgendaModel.objects.filter(pk=agenda.id).update(cities=cities)
        WeeklySlotModel.objects.filter(agenda_id=agenda.id).delete()
        WeeklySlotModel.objects.bulk_create(
            [WeeklySlotModel(agenda_id=agenda.id, weekday=s.weekday, start=s.start, end=s.end) for s in slots])

    def add_exception(self, agenda, exception):
        m = AvailabilityExceptionModel.objects.create(agenda_id=agenda.id, day=exception.day, kind=exception.kind,
                                                      start=exception.start, end=exception.end)
        return AvailabilityException(id=m.id, day=m.day, kind=m.kind, start=m.start, end=m.end)

    def delete_exception(self, agenda, exception_id):
        deleted, _ = AvailabilityExceptionModel.objects.filter(agenda_id=agenda.id, pk=exception_id).delete()
        return bool(deleted)

    def set_day_limit(self, agenda, day, max_visits):
        if max_visits is None:
            DayLimitModel.objects.filter(agenda_id=agenda.id, day=day).delete()
        else:
            DayLimitModel.objects.update_or_create(agenda_id=agenda.id, day=day, defaults={'max_visits': max_visits})

    def regenerate_token(self, agenda):
        token = new_token()
        AgendaModel.objects.filter(pk=agenda.id).update(ics_token=token)
        return token

    def mark_availability_reminder(self, agenda, moment):
        AgendaModel.objects.filter(pk=agenda.id).update(availability_reminder_at=moment)


FIELDS = ('agent_id', 'requester_id', 'city', 'address', 'start', 'end', 'blocked_until', 'status', 'origin',
          'waiting_since', 'created_at', 'on_the_way_at', 'done_at', 'cancelled_at', 'cancelled_by',
          'cancellation_reason', 'sequence', 'host_reminder_at', 'alert_at')


def _coordinate(value):
    return None if value is None else float(value)


def _target_json(t: Target) -> dict:
    return {'id': t.id, 'title': t.title, 'latitude': _coordinate(t.latitude), 'longitude': _coordinate(t.longitude)}


def _appointment(m: AppointmentModel) -> Appointment:
    return Appointment(
        id=m.id, agenda_id=m.agenda_id,
        targets=[Target(id=t['id'], title=t.get('title', ''), latitude=t.get('latitude'),
                        longitude=t.get('longitude')) for t in m.targets],
        **{name: getattr(m, name) for name in FIELDS},
    )


def _values(a: Appointment) -> dict:
    return {'agenda_id': a.agenda_id, 'targets': [_target_json(t) for t in a.targets],
            **{name: getattr(a, name) for name in FIELDS}}


class DjangoAppointmentRepository(AppointmentRepository):
    def _write(self, write):
        try:
            with transaction.atomic():
                return write()
        except IntegrityError as exc:
            if NO_OVERLAP in str(exc):
                raise SlotUnavailable("Ce créneau vient d'être pris : choisissez-en un autre.") from None
            raise

    def add(self, appointment):
        return _appointment(self._write(lambda: AppointmentModel.objects.create(**_values(appointment))))

    def save(self, appointment):
        def write():
            AppointmentModel.objects.filter(pk=appointment.id).update(**_values(appointment))
            return AppointmentModel.objects.get(pk=appointment.id)

        return _appointment(self._write(write))

    def get(self, appointment_id):
        m = AppointmentModel.objects.filter(pk=appointment_id).first()
        return _appointment(m) if m else None

    def active_for_agendas(self, agenda_ids, start, end):
        qs = AppointmentModel.objects.filter(agenda_id__in=agenda_ids, status__in=ACTIVE, start__lt=end,
                                             blocked_until__gt=start)
        return [_appointment(m) for m in qs]

    def between(self, start, end, agent_id=None, with_cancelled=False):
        qs = AppointmentModel.objects.filter(start__lt=end, end__gt=start)
        if agent_id is not None:
            qs = qs.filter(agent_id=agent_id)
        if not with_cancelled:
            qs = qs.filter(status__in=ACTIVE)
        return [_appointment(m) for m in qs.order_by('start')]

    def lock_targets(self, target_ids):
        with connection.cursor() as cursor:
            for target in sorted(set(target_ids)):
                key = int.from_bytes(hashlib.sha256(f'agenda:{target}'.encode()).digest()[:8], 'big', signed=True)
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [key])

    def confirmed_for_targets(self, target_ids):
        if not target_ids:
            return []
        qs = AppointmentModel.objects.none()
        for target in target_ids:
            qs = qs | AppointmentModel.objects.filter(targets__contains=[{'id': str(target)}])
        return [_appointment(m) for m in qs.filter(status=CONFIRMED).order_by('start')]

    def feed(self, agenda_id, since):
        return [_appointment(m) for m in AppointmentModel.objects.filter(agenda_id=agenda_id, end__gte=since)]

    def without_decision(self, before):
        qs = AppointmentModel.objects.filter(status=CONFIRMED, end__lt=before, alert_at__isnull=True)
        return [_appointment(m) for m in qs]

    def created_since(self, since):
        return [_appointment(m) for m in AppointmentModel.objects.filter(created_at__gte=since, status__in=ACTIVE)]


class DjangoDigestRepository(DigestRepository):
    def mark(self, agenda_id, day, moment):
        _, created = DigestModel.objects.get_or_create(agenda_id=agenda_id, day=day, defaults={'sent_at': moment})
        return created
