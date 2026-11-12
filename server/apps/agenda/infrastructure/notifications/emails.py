import logging
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string

from apps.agenda.application.ports import Notifier, PeopleLookup
from apps.notifications.api import send_mail

logger = logging.getLogger('apps.agenda')

WEEKDAYS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre',
          'novembre', 'décembre']


def hour(moment, tz) -> str:
    local = moment.astimezone(tz)
    return f"{local.hour} h {local.minute:02d}".replace(' h 00', ' h')


def day(value) -> str:
    return f"{WEEKDAYS[value.weekday()]} {value.day} {MONTHS[value.month - 1]}"


def when(moment, tz) -> str:
    return f"{day(moment.astimezone(tz).date())} à {hour(moment, tz)}"


def _url(path: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def _send(template: str, subject: str, recipients: list[str], context: dict) -> None:
    def send():
        try:
            send_mail(subject, render_to_string(f'emails/agenda/{template}.txt', context), settings.DEFAULT_FROM_EMAIL,
                      recipients)
        except Exception:
            logger.exception("Email %s not sent", template)

    if recipients:
        transaction.on_commit(send)


class EmailNotifier(Notifier):
    def __init__(self, people: PeopleLookup):
        self.people = people

    def _to_host(self, template: str, subject: str, appointment, agenda, **context) -> None:
        host = self.people.person(appointment.requester_id)
        if host is None:
            return
        _send(template, subject, [host.email], {
            'title': appointment.title, 'listings': [t.title for t in appointment.targets],
            'city': appointment.city, 'when': when(appointment.start, agenda.tz),
            'url': _url('/hote/espace/visite'), **context,
        })

    def _to_agent(self, agent_id, template: str, subject: str, appointment, agenda, **context) -> None:
        agent = self.people.person(agent_id)
        if agent is None:
            return
        _send(template, subject, [agent.email], {
            'title': appointment.title, 'listings': [t.title for t in appointment.targets],
            'city': appointment.city, 'when': when(appointment.start, agenda.tz),
            'url': _url(f'/agent/agenda/{appointment.id}'), **context,
        })

    def confirmed(self, appointment, agenda):
        self._to_host('confirmed', f"Visite confirmée le {when(appointment.start, agenda.tz)}", appointment, agenda,
                      by_phone=appointment.origin == 'phone')
        if appointment.origin == 'host':
            self._to_agent(appointment.agent_id, 'agent_booked',
                           f"[Kwa-Ba] Nouvelle visite le {when(appointment.start, agenda.tz)}", appointment, agenda)

    def moved(self, appointment, agenda):
        self._to_host('moved', f"Visite déplacée au {when(appointment.start, agenda.tz)}", appointment, agenda)
        self._to_agent(appointment.agent_id, 'agent_moved',
                       f"[Kwa-Ba] Visite déplacée au {when(appointment.start, agenda.tz)}", appointment, agenda)

    def reassigned(self, appointment, agenda, previous_agent_id):
        self._to_agent(appointment.agent_id, 'agent_booked',
                       f"[Kwa-Ba] Nouvelle visite le {when(appointment.start, agenda.tz)}", appointment, agenda,
                       reassigned=True)
        self._to_agent(previous_agent_id, 'agent_unassigned',
                       f"[Kwa-Ba] Visite confiée à un autre agent : {appointment.title}", appointment, agenda,
                       url=_url('/agent/agenda'))

    def cancelled(self, appointment, agenda):
        if appointment.cancelled_by == 'host':
            return
        self._to_host('cancelled', "Votre visite est annulée", appointment, agenda,
                      reason=appointment.cancellation_reason)

    def host_reminder(self, appointment, agenda):
        self._to_host('host_reminder', f"Rappel : visite demain à {hour(appointment.start, agenda.tz)}", appointment,
                      agenda, hour=hour(appointment.start, agenda.tz))

    def on_the_way(self, appointment, agenda):
        self._to_host('on_the_way', "L'agent Kwa-Ba est en route", appointment, agenda,
                      hour=hour(appointment.start, agenda.tz))

    def agent_digest(self, agenda, visit_day, appointments):
        agent = self.people.person(agenda.agent_id)
        if agent is None:
            return
        visits = [{'hour': hour(a.start, agenda.tz), 'title': a.title, 'city': a.city} for a in appointments]
        _send('agent_digest', f"[Kwa-Ba] Vos visites de demain ({len(appointments)})", [agent.email], {
            'day': day(visit_day), 'visits': visits, 'url': _url('/agent/agenda'),
        })

    def availability_reminder(self, agent_id):
        agent = self.people.person(agent_id)
        if agent is None:
            return
        _send('availability_reminder', "[Kwa-Ba] Publiez vos disponibilités", [agent.email],
              {'url': _url('/agent/agenda/disponibilites')})

    def visits_without_decision(self, appointments):
        agents = self.people.people({a.agent_id for a in appointments})
        tz = ZoneInfo(settings.AGENDA['TIMEZONE'])
        visits = [{'when': when(a.start, tz), 'title': a.title, 'city': a.city,
                   'agent': agents[a.agent_id].name if a.agent_id in agents else '-'} for a in appointments]
        _send('visits_without_decision', f"[Kwa-Ba] Visites passées sans décision ({len(appointments)})",
              self.people.admin_emails(), {'visits': visits, 'url': _url('/agent/agenda')})
