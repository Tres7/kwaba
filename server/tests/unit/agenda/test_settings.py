from datetime import timedelta

import pytest

from apps.agenda.domain.settings import AgendaSettings, InvalidSettings, to_rules, validated


def test_defaults_are_the_validated_rules():
    rules = to_rules(AgendaSettings())
    assert rules.notice == timedelta(hours=24) and rules.horizon == timedelta(days=14)
    assert rules.max_per_day == 4 and rules.margin == timedelta(minutes=30)
    assert rules.visit_duration == timedelta(hours=1) and rules.extra_listing == timedelta(minutes=20)
    assert rules.max_listings == 5 and rules.same_site_distance_m == 200


def test_changes_within_bounds():
    changed = validated(AgendaSettings(), {'notice_hours': 48, 'visit_minutes': 90, 'unknown': 3})
    assert changed.notice_hours == 48 and changed.visit_minutes == 90 and changed.max_per_day == 4


@pytest.mark.parametrize('name,value', [
    ('notice_hours', 0), ('notice_hours', 73), ('horizon_days', 6), ('max_per_day', 11), ('margin_minutes', 121),
    ('visit_minutes', 29), ('extra_listing_minutes', 61), ('max_listings', 0), ('same_site_distance_m', 1001),
    ('digest_hour', 23), ('decision_alert_hours', 49), ('host_reminder_days', 15), ('notice_hours', '24'),
    ('notice_hours', True),
])
def test_out_of_bounds(name, value):
    with pytest.raises(InvalidSettings) as refused:
        validated(AgendaSettings(), {name: value})
    assert name in refused.value.errors


def test_the_admin_alert_comes_after_the_host_reminder():
    with pytest.raises(InvalidSettings) as refused:
        validated(AgendaSettings(), {'host_reminder_days': 3, 'host_alert_days': 3})
    assert 'host_alert_days' in refused.value.errors
