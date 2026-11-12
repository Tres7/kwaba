from datetime import timedelta

from django.conf import settings

from apps.agenda.application.service import AgendaService, Settings
from apps.agenda.application.tasks import tasks
from apps.agenda.domain.rules import Rules
from apps.agenda.infrastructure.clock import DjangoClock
from apps.agenda.infrastructure.lookups.users import DjangoPeopleLookup
from apps.agenda.infrastructure.notifications.emails import EmailNotifier
from apps.agenda.infrastructure.persistence.repositories import (
    DjangoAgendaRepository, DjangoAppointmentRepository, DjangoDigestRepository, DjangoTransactionManager,
)


def rules() -> Rules:
    config = settings.AGENDA
    return Rules(
        visit_duration=timedelta(minutes=config['VISIT_DURATION_MIN']),
        extra_listing=timedelta(minutes=config['EXTRA_LISTING_MIN']),
        max_listings=config['MAX_LISTINGS'],
        margin=timedelta(minutes=config['MARGIN_MIN']),
        max_per_day=config['MAX_PER_DAY'],
        per_day_ceiling=config['PER_DAY_CEILING'],
        notice=timedelta(hours=config['NOTICE_H']),
        horizon=timedelta(days=config['HORIZON_DAYS']),
        step=timedelta(minutes=config['STEP_MIN']),
        same_site_distance_m=config['SAME_SITE_DISTANCE_M'],
    )


def agenda_service() -> AgendaService:
    config = settings.AGENDA
    people = DjangoPeopleLookup()
    return AgendaService(
        agendas=DjangoAgendaRepository(),
        appointments=DjangoAppointmentRepository(),
        digests=DjangoDigestRepository(),
        people=people,
        notifier=EmailNotifier(people),
        tx=DjangoTransactionManager(),
        clock=DjangoClock(),
        rules=rules(),
        settings=Settings(
            digest_hour=config['DIGEST_HOUR'],
            decision_delay=timedelta(hours=config['DECISION_DELAY_H']),
        ),
        tasks=tasks,
    )
