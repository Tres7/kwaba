from datetime import timedelta

from apps.agenda.application.service import AgendaService, Settings
from apps.agenda.application.tasks import tasks
from apps.agenda.domain.settings import AgendaSettings, to_rules
from apps.agenda.infrastructure.clock import DjangoClock
from apps.agenda.infrastructure.lookups.users import DjangoPeopleLookup
from apps.agenda.infrastructure.notifications.emails import EmailNotifier
from apps.agenda.infrastructure.persistence.repositories import (
    DjangoAgendaRepository, DjangoAppointmentRepository, DjangoDigestRepository, DjangoSettingsRepository,
    DjangoTransactionManager,
)


def current_settings() -> AgendaSettings:
    return DjangoSettingsRepository().load().values


def agenda_service() -> AgendaService:
    values = current_settings()
    people = DjangoPeopleLookup()
    return AgendaService(
        agendas=DjangoAgendaRepository(),
        appointments=DjangoAppointmentRepository(),
        digests=DjangoDigestRepository(),
        settings_store=DjangoSettingsRepository(),
        people=people,
        notifier=EmailNotifier(people),
        tx=DjangoTransactionManager(),
        clock=DjangoClock(),
        rules=to_rules(values),
        settings=Settings(
            digest_hour=values.digest_hour,
            decision_delay=timedelta(hours=values.decision_alert_hours),
        ),
        tasks=tasks,
    )
