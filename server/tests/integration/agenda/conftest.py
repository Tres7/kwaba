from datetime import date, datetime, time, timedelta, timezone

import pytest

from apps.agenda.infrastructure.clock import DjangoClock
from apps.agenda.models import AgendaModel, AppointmentModel, WeeklySlotModel


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=timezone.utc)


def in_days(days: int) -> date:
    return (datetime.now(timezone.utc) + timedelta(days=days)).date()


@pytest.fixture
def make_agenda():
    def _make(agent, cities=('Lomé',), start=time(8), end=time(18), weekdays=range(7)):
        agenda, _ = AgendaModel.objects.get_or_create(agent_id=agent.pk)
        agenda.cities = list(cities)
        agenda.save(update_fields=['cities'])
        WeeklySlotModel.objects.bulk_create(
            [WeeklySlotModel(agenda=agenda, weekday=d, start=start, end=end) for d in weekdays])
        return agenda

    return _make


@pytest.fixture
def make_appointment(make_user):
    def _make(agenda, start, minutes=60, status='confirmed', requester=None, targets=None, **fields):
        end = start + timedelta(minutes=minutes)
        return AppointmentModel.objects.create(
            agenda=agenda, agent_id=agenda.agent_id, requester_id=(requester or make_user(role='hote')).pk,
            targets=targets or [{'id': 'listing-1', 'title': 'Studio meublé'}], city='Lomé', start=start, end=end,
            blocked_until=end + timedelta(minutes=30), status=status, created_at=datetime.now(timezone.utc),
            **fields)

    return _make


@pytest.fixture
def frozen_clock(monkeypatch):
    def _freeze(moment: datetime):
        monkeypatch.setattr(DjangoClock, 'now', lambda self: moment)

    return _freeze
