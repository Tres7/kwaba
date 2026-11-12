from urllib.parse import urlsplit

from django.conf import settings

from apps.agenda.domain.entities import CANCELLED, Appointment
from apps.export import api as export

PRODID = '-//Kwa-Ba//Agenda//FR'


def _domain() -> str:
    return urlsplit(settings.FRONTEND_URL).hostname or 'kwa-ba.com'


def _event(appointment: Appointment) -> export.Event:
    title = f"Visite · {appointment.title}"
    cancelled = appointment.status == CANCELLED
    return export.Event(
        uid=f'visit-{appointment.id}@{_domain()}',
        start=appointment.start,
        end=appointment.end,
        title=title,
        location=appointment.city,
        url=f"{settings.FRONTEND_URL.rstrip('/')}/agent/agenda/{appointment.id}",
        status='CANCELLED' if cancelled else 'CONFIRMED',
        sequence=appointment.sequence,
        alarm='' if cancelled else '-PT1H',
        alarm_text=title,
    )


def single_visit(appointment: Appointment) -> str:
    return export.calendar([_event(appointment)], prodid=PRODID)


def agent_feed(appointments: list[Appointment]) -> str:
    return export.calendar([_event(a) for a in appointments], prodid=PRODID, name='Kwa-Ba · Visites')


def filename(appointment: Appointment) -> str:
    return f"kwa-ba-visite-{appointment.start:%Y%m%d-%H%M}.ics"
