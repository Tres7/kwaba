import datetime

import pytest

from apps.messaging.domain.services.SanctionLadder import (
    ADMIN_DECISION, FORMAL_WARNING, LONG_SUSPENSION, REMINDER, SHORT_SUSPENSION, AppliedSuspension, LadderPolicy,
    evaluate,
)

POLICY = LadderPolicy()
T0 = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def day(n: float) -> datetime.datetime:
    return T0 + datetime.timedelta(days=n)


def outcome(cases, suspensions=(), decisions=0, now=None):
    return evaluate([day(c) for c in cases], list(suspensions), decisions, POLICY, now or day(max(cases) + 1))


@pytest.mark.parametrize('cases,step', [
    ([1], REMINDER),
    ([1, 2], REMINDER),
    ([1, 2, 3], FORMAL_WARNING),
    ([1, 2, 3, 4], FORMAL_WARNING),
])
def test_first_cases_escalate_from_reminder_to_formal_warning(cases, step):
    assert outcome(cases).step == step


def test_fifth_case_in_window_suspends_from_confirmation():
    now = day(10)
    result = outcome([1, 2, 3, 4, 5], now=now)
    assert result.step == SHORT_SUSPENSION
    assert (result.starts_at, result.ends_at) == (now, now + datetime.timedelta(hours=24))


def test_cases_outside_the_sliding_window_do_not_add_up():
    assert outcome([1, 2, 40, 41]).step == REMINDER
    assert outcome([1, 2, 3, 4, 40]).step == REMINDER


def test_late_confirmation_is_replayed_by_message_date():
    assert outcome([1, 2, 3, 4, 0.5], now=day(20)).step == SHORT_SUSPENSION


def test_one_case_after_short_suspension_triggers_long_suspension():
    short = AppliedSuspension(SHORT_SUSPENSION, day(10), day(11))
    now = day(15)
    result = outcome([1, 2, 3, 4, 5, 14], [short], now=now)
    assert result.step == LONG_SUSPENSION
    assert result.ends_at == now + datetime.timedelta(days=7)


def test_case_sent_before_suspension_end_is_absorbed():
    short = AppliedSuspension(SHORT_SUSPENSION, day(10), day(11))
    assert outcome([1, 2, 3, 4, 5, 6], [short], now=day(12)).step == REMINDER


def test_counter_restarts_after_suspension():
    short = AppliedSuspension(SHORT_SUSPENSION, day(10), day(11))
    result = outcome([1, 2, 3, 4, 5, 45], [short], now=day(46))
    assert result.step == REMINDER
    assert result.level == 0


def test_case_after_long_suspension_goes_to_admin():
    suspensions = [AppliedSuspension(SHORT_SUSPENSION, day(10), day(11)),
                   AppliedSuspension(LONG_SUSPENSION, day(15), day(22))]
    assert outcome([1, 2, 3, 4, 5, 14, 30], suspensions).step == ADMIN_DECISION
    assert outcome([1, 2, 3, 4, 5, 14, 30], suspensions, decisions=1).step == REMINDER
    assert outcome([1, 2, 3, 4, 5, 14, 30, 35], suspensions, decisions=1).step == ADMIN_DECISION


def test_level_decays_after_thirty_quiet_days():
    suspensions = [AppliedSuspension(SHORT_SUSPENSION, day(10), day(11)),
                   AppliedSuspension(LONG_SUSPENSION, day(15), day(22))]
    result = outcome([1, 2, 3, 4, 5, 14, 60], suspensions)
    assert (result.step, result.level) == (REMINDER, 0)


def test_already_applied_suspension_is_never_applied_twice():
    short = AppliedSuspension(SHORT_SUSPENSION, day(10), day(11))
    assert outcome([1, 2, 3, 4, 5], [short], now=day(10)).step == REMINDER


def test_thresholds_come_from_the_policy():
    policy = LadderPolicy(warning_threshold=2, suspension_threshold=3)
    assert evaluate([day(1), day(2)], [], 0, policy, day(3)).step == FORMAL_WARNING
    assert evaluate([day(1), day(2), day(3)], [], 0, policy, day(4)).step == SHORT_SUSPENSION
