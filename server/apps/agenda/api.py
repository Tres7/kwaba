import uuid
from datetime import datetime

from apps.agenda.application.service import BY_ADMIN, BY_AGENT, BY_HOST, BookingRequest
from apps.agenda.application.tasks import register_task
from apps.agenda.domain.entities import Appointment, Target
from apps.agenda.domain.exceptions import AgendaError
from apps.agenda.domain.settings import DEFAULT_TIMEZONE, AgendaSettings
from apps.agenda.infrastructure.container import agenda_service, current_settings

__all__ = [
    'AgendaError', 'AgendaSettings', 'Appointment', 'DEFAULT_TIMEZONE', 'settings', 'BY_ADMIN', 'BY_AGENT', 'BY_HOST', 'BookingRequest', 'Target', 'appointment',
    'book', 'book_by_phone', 'cancel', 'close', 'confirmed_for_targets', 'free_slots', 'keep_as_post_check', 'move', 'reassign',
    'register_task', 'summary',
]


def summary(appointment: Appointment) -> dict:
    return {
        'id': str(appointment.id), 'agent_id': str(appointment.agent_id),
        'requester_id': str(appointment.requester_id),
        'listings': [{'id': t.id, 'title': t.title} for t in appointment.targets], 'city': appointment.city,
        'start': appointment.start, 'end': appointment.end, 'status': appointment.status,
        'origin': appointment.origin, 'on_the_way_at': appointment.on_the_way_at,
    }


def settings() -> AgendaSettings:
    return current_settings()


def free_slots(city: str, listing_count: int, agent_id: uuid.UUID | None = None,
               exclude: uuid.UUID | None = None) -> list[datetime]:
    return agenda_service().free_slots(city, listing_count, agent_id, exclude)


def book(request: BookingRequest) -> Appointment:
    return agenda_service().book(request)


def book_by_phone(agent_id: uuid.UUID, request: BookingRequest) -> Appointment:
    return agenda_service().book_by_phone(agent_id, request)


def move(appointment_id: uuid.UUID, requester_id: uuid.UUID, start: datetime) -> Appointment:
    return agenda_service().move(appointment_id, requester_id, start)


def cancel(appointment_id: uuid.UUID, *, author_id: uuid.UUID, by: str, reason: str,
           notify: bool = True) -> Appointment:
    return agenda_service().cancel(appointment_id, author_id=author_id, by=by, reason=reason, notify=notify)


def keep_as_post_check(appointment_id: uuid.UUID) -> Appointment:
    return agenda_service().keep_as_post_check(appointment_id)


def reassign(appointment_id: uuid.UUID, agent_id: uuid.UUID) -> Appointment:
    return agenda_service().reassign(appointment_id, agent_id)


def appointment(appointment_id: uuid.UUID) -> Appointment:
    return agenda_service().get(appointment_id)


def confirmed_for_targets(target_ids) -> list[Appointment]:
    return agenda_service().confirmed_for_targets(target_ids)


def close(appointment_id: uuid.UUID, reason: str = '') -> Appointment:
    return agenda_service().close(appointment_id, reason)
