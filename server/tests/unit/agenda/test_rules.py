import uuid
from datetime import date, datetime, time, timedelta, timezone

import pytest

from apps.agenda.domain import rules as r
from apps.agenda.domain.entities import (
    BLOCK, CANCELLED, EXTRA, Agenda, Appointment, AvailabilityException, Target, WeeklySlot,
)
from apps.agenda.domain.exceptions import DailyLimitReached, InvalidRule, SlotUnavailable

RULES = r.Rules()
MONDAY = date(2026, 11, 16)
NOW = datetime(2026, 11, 12, 8, 0, tzinfo=timezone.utc)


def utc(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=timezone.utc)


def make_agenda(**fields) -> Agenda:
    values = {'agent_id': uuid.uuid4(), 'id': uuid.uuid4(), 'cities': ['Lomé'],
              'weekly_slots': [WeeklySlot(weekday=d, start=time(8), end=time(18)) for d in range(5)]}
    return Agenda(**{**values, **fields})


def make_appointment(agenda: Agenda, start: datetime, minutes: int = 60, status: str = 'confirmed') -> Appointment:
    end = start + timedelta(minutes=minutes)
    return Appointment(id=uuid.uuid4(), agenda_id=agenda.id, agent_id=agenda.agent_id, requester_id=uuid.uuid4(),
                       targets=[Target(id=str(uuid.uuid4()), title='Studio')], city='Lomé', start=start, end=end,
                       blocked_until=end + RULES.margin, status=status)


def check(agenda, appointments, start, minutes=60, **options):
    r.check(agenda, appointments, start, timedelta(minutes=minutes), now=NOW, rules=RULES, **options)


class TestDuration:
    def test_one_listing_lasts_sixty_minutes(self):
        assert r.duration(1, RULES) == timedelta(minutes=60)

    def test_each_extra_listing_adds_twenty_minutes(self):
        assert r.duration(3, RULES) == timedelta(minutes=100)
        assert r.duration(5, RULES) == timedelta(minutes=140)

    @pytest.mark.parametrize('count', [0, 6])
    def test_group_size_is_bounded(self, count):
        with pytest.raises(InvalidRule):
            r.duration(count, RULES)


class TestSameSite:
    def test_listings_within_two_hundred_metres(self):
        targets = [Target('a', 'A', 6.1300, 1.2200), Target('b', 'B', 6.1310, 1.2205)]
        r.check_same_site(targets, RULES)

    def test_listings_too_far_apart(self):
        targets = [Target('a', 'A', 6.1300, 1.2200), Target('b', 'B', 6.1400, 1.2200)]
        with pytest.raises(InvalidRule, match='même site'):
            r.check_same_site(targets, RULES)

    def test_a_listing_without_position_cannot_be_grouped(self):
        with pytest.raises(InvalidRule, match='position'):
            r.check_same_site([Target('a', 'A', 6.13, 1.22), Target('b', 'B')], RULES)

    def test_a_single_listing_needs_no_position(self):
        r.check_same_site([Target('a', 'A')], RULES)

    def test_the_same_listing_twice_is_refused(self):
        with pytest.raises(InvalidRule):
            r.check_same_site([Target('a', 'A', 6.13, 1.22), Target('a', 'A', 6.13, 1.22)], RULES)


class TestCity:
    def test_matching_ignores_accents_case_and_dashes(self):
        agenda = make_agenda(cities=['Lomé', 'Agbodrafo'])
        assert r.covers(agenda, ' LOME ')
        assert r.covers(agenda, 'agbodrafo')
        assert not r.covers(agenda, 'Kpalimé')
        assert not r.covers(agenda, '')


class TestDayWindows:
    def test_weekly_slot(self):
        assert r.day_windows(make_agenda(), MONDAY) == [(utc(MONDAY, 8), utc(MONDAY, 18))]

    def test_nothing_on_a_day_without_slot(self):
        assert r.day_windows(make_agenda(), MONDAY + timedelta(days=5)) == []

    def test_whole_day_blocked(self):
        agenda = make_agenda(exceptions=[AvailabilityException(day=MONDAY, kind=BLOCK)])
        assert r.day_windows(agenda, MONDAY) == []

    def test_part_of_the_day_blocked(self):
        agenda = make_agenda(exceptions=[AvailabilityException(day=MONDAY, kind=BLOCK, start=time(12), end=time(14))])
        assert r.day_windows(agenda, MONDAY) == [(utc(MONDAY, 8), utc(MONDAY, 12)), (utc(MONDAY, 14), utc(MONDAY, 18))]

    def test_one_off_addition_on_a_saturday(self):
        saturday = MONDAY + timedelta(days=5)
        agenda = make_agenda(exceptions=[AvailabilityException(day=saturday, kind=EXTRA, start=time(9), end=time(12))])
        assert r.day_windows(agenda, saturday) == [(utc(saturday, 9), utc(saturday, 12))]

    def test_overlapping_windows_are_merged(self):
        agenda = make_agenda(exceptions=[AvailabilityException(day=MONDAY, kind=EXTRA, start=time(17), end=time(20))])
        assert r.day_windows(agenda, MONDAY) == [(utc(MONDAY, 8), utc(MONDAY, 20))]

    def test_slots_are_read_in_the_agenda_time_zone(self):
        agenda = make_agenda(timezone='Africa/Lagos')
        assert r.day_windows(agenda, MONDAY) == [(utc(MONDAY, 7), utc(MONDAY, 17))]


class TestBooking:
    def test_free_slot(self):
        check(make_agenda(), [], utc(MONDAY, 9))

    def test_notice_of_twenty_four_hours(self):
        with pytest.raises(SlotUnavailable, match='24 h'):
            check(make_agenda(), [], NOW + timedelta(hours=23))

    def test_horizon_of_fourteen_days(self):
        with pytest.raises(SlotUnavailable, match='14'):
            check(make_agenda(), [], utc(MONDAY + timedelta(days=14), 9))

    def test_the_visit_must_fit_in_the_slot(self):
        with pytest.raises(SlotUnavailable):
            check(make_agenda(), [], utc(MONDAY, 17, 30))

    def test_the_margin_may_overflow_the_slot(self):
        check(make_agenda(), [], utc(MONDAY, 17))

    def test_overlap_is_refused(self):
        agenda = make_agenda()
        with pytest.raises(SlotUnavailable):
            check(agenda, [make_appointment(agenda, utc(MONDAY, 9))], utc(MONDAY, 9, 30))

    def test_thirty_minutes_after_a_visit(self):
        agenda = make_agenda()
        appointments = [make_appointment(agenda, utc(MONDAY, 9))]
        with pytest.raises(SlotUnavailable):
            check(agenda, appointments, utc(MONDAY, 10))
        check(agenda, appointments, utc(MONDAY, 10, 30))

    def test_thirty_minutes_before_the_next_visit(self):
        agenda = make_agenda()
        appointments = [make_appointment(agenda, utc(MONDAY, 11))]
        with pytest.raises(SlotUnavailable):
            check(agenda, appointments, utc(MONDAY, 10))
        check(agenda, appointments, utc(MONDAY, 9, 30))

    def test_the_margin_recorded_on_a_booking_is_kept(self):
        agenda = make_agenda()
        previous = make_appointment(agenda, utc(MONDAY, 9))
        previous.blocked_until = previous.end + timedelta(minutes=10)
        check(agenda, [previous], utc(MONDAY, 10, 10))

    def test_a_cancelled_visit_frees_its_slot(self):
        agenda = make_agenda()
        check(agenda, [make_appointment(agenda, utc(MONDAY, 9), status=CANCELLED)], utc(MONDAY, 9))

    def test_four_visits_a_day(self):
        agenda = make_agenda()
        appointments = [make_appointment(agenda, utc(MONDAY, hour)) for hour in (8, 10, 12, 14)]
        with pytest.raises(DailyLimitReached):
            check(agenda, appointments, utc(MONDAY, 16))

    def test_raised_limit_for_one_day(self):
        agenda = make_agenda(day_limits={MONDAY: 5})
        check(agenda, [make_appointment(agenda, utc(MONDAY, hour)) for hour in (8, 10, 12, 14)], utc(MONDAY, 16))

    def test_moving_a_visit_does_not_count_itself(self):
        agenda = make_agenda()
        appointments = [make_appointment(agenda, utc(MONDAY, hour)) for hour in (8, 10, 12, 14)]
        check(agenda, appointments, utc(MONDAY, 15), exclude=appointments[-1].id)

    def test_phone_booking_skips_availability_and_notice(self):
        agenda = make_agenda(weekly_slots=[])
        check(agenda, [], NOW + timedelta(hours=2), check_availability=False)


class TestSlots:
    def test_slots_every_thirty_minutes(self):
        agenda = make_agenda(weekly_slots=[WeeklySlot(weekday=0, start=time(9), end=time(11))])
        found = r.free_slots(agenda, [], timedelta(minutes=60), now=NOW, rules=RULES)
        assert found[:3] == [utc(MONDAY, 9), utc(MONDAY, 9, 30), utc(MONDAY, 10)]
        assert all(t.weekday() == 0 for t in found)

    def test_no_slot_within_the_notice(self):
        agenda = make_agenda()
        found = r.free_slots(agenda, [], timedelta(minutes=60), now=NOW, rules=RULES)
        assert min(found) >= NOW + RULES.notice
        assert max(found) <= NOW + RULES.horizon

    def test_taken_slots_and_full_days_are_hidden(self):
        agenda = make_agenda(weekly_slots=[WeeklySlot(weekday=0, start=time(8), end=time(18))])
        appointments = [make_appointment(agenda, utc(MONDAY, 9))]
        found = r.free_slots(agenda, appointments, timedelta(minutes=60), now=NOW, rules=RULES)
        assert utc(MONDAY, 9, 30) not in found and utc(MONDAY, 10, 30) in found
        full = [make_appointment(agenda, utc(MONDAY, hour)) for hour in (8, 10, 12, 14)]
        found = r.free_slots(agenda, full, timedelta(minutes=60), now=NOW, rules=RULES)
        assert not [t for t in found if t.date() == MONDAY]

    def test_longer_group_visits_get_fewer_slots(self):
        agenda = make_agenda(weekly_slots=[WeeklySlot(weekday=0, start=time(9), end=time(11))])
        found = r.free_slots(agenda, [], timedelta(minutes=100), now=NOW, rules=RULES)
        assert [t for t in found if t.date() == MONDAY] == [utc(MONDAY, 9)]


class TestAvailability:
    def test_agenda_without_slot(self):
        assert not r.has_availability(make_agenda(weekly_slots=[]), NOW, RULES)

    def test_one_off_addition_is_enough(self):
        agenda = make_agenda(weekly_slots=[], exceptions=[AvailabilityException(day=MONDAY, kind=EXTRA, start=time(9),
                                                                   end=time(10))])
        assert r.has_availability(agenda, NOW, RULES)


class TestAgentChoice:
    def test_least_busy_agent_that_day_then_over_the_period(self):
        busy, free, quiet = make_agenda(), make_agenda(), make_agenda()
        candidates = [
            (busy, [make_appointment(busy, utc(MONDAY, 8))]),
            (free, [make_appointment(free, utc(MONDAY + timedelta(days=1), 8)) for _ in range(2)]),
            (quiet, [make_appointment(quiet, utc(MONDAY + timedelta(days=1), 8))]),
        ]
        assert r.choose(candidates, utc(MONDAY, 10)) is quiet


class TestClosedVisits:
    def test_a_visit_closed_before_its_start_frees_the_slot(self):
        agenda = make_agenda()
        early = make_appointment(agenda, utc(MONDAY, 9), status='done')
        early.done_at = utc(MONDAY, 8) - timedelta(days=2)
        check(agenda, [early], utc(MONDAY, 9))

    def test_a_visit_done_on_time_still_counts(self):
        agenda = make_agenda()
        done = make_appointment(agenda, utc(MONDAY, 9), status='done')
        done.done_at = utc(MONDAY, 10)
        with pytest.raises(SlotUnavailable):
            check(agenda, [done], utc(MONDAY, 9, 30), check_availability=False)
