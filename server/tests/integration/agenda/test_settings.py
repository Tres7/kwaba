from datetime import timedelta

import pytest

from apps.agenda import api as agenda
from apps.agenda.models import AgendaSettingsModel, AppointmentModel
from apps.activity.models import ActivityEntryModel

from .conftest import at, in_days

URL = '/api/v1/admin/agenda/settings/'


@pytest.fixture
def super_admin(make_user):
    return make_user(role='admin', is_superuser=True, is_staff=True)


def test_defaults_without_any_saved_row(super_admin, client_for):
    data = client_for(super_admin).get(URL).data
    assert data['values'] == data['defaults'] and data['values']['notice_hours'] == 24
    assert data['bounds']['notice_hours'] == {'min': 1, 'max': 72}
    assert data['updated_at'] is None and not AgendaSettingsModel.objects.exists()


def test_a_change_is_audited_with_before_and_after(super_admin, client_for):
    response = client_for(super_admin).put(URL, {'notice_hours': 48, 'max_per_day': 4}, format='json')
    assert response.status_code == 200
    assert response.data['values']['notice_hours'] == 48 and response.data['updated_by']
    entry = ActivityEntryModel.objects.get(action='agenda_settings_changed')
    assert entry.details['changes'] == {'notice_hours': {'before': 24, 'after': 48}}


def test_out_of_bounds_values_are_refused(super_admin, client_for):
    response = client_for(super_admin).put(URL, {'notice_hours': 100}, format='json')
    assert response.status_code == 400 and 'notice_hours' in response.data['errors']
    assert not AgendaSettingsModel.objects.exists()


def test_reserved_to_super_admins_and_granted_admins(make_user, client_for):
    unlimited = make_user(role='admin')
    assert client_for(unlimited).get(URL).status_code == 403
    granted = make_user(role='admin', admin_permissions=['agenda_settings'])
    assert client_for(granted).get(URL).status_code == 200
    without_section = make_user(role='admin', admin_permissions=['agenda_settings'], admin_sections=['avis'])
    assert client_for(without_section).get(URL).status_code == 403
    assert client_for(make_user(role='agent')).get(URL).status_code == 403


def test_new_rules_apply_to_new_bookings_only(super_admin, client_for, make_user, make_agenda, make_appointment):
    calendar = make_agenda(make_user(role='agent'))
    booked = make_appointment(calendar, at(in_days(3), 9))
    client_for(super_admin).put(URL, {'visit_minutes': 90, 'margin_minutes': 60, 'notice_hours': 72}, format='json')
    booked.refresh_from_db()
    assert booked.end - booked.start == timedelta(hours=1)
    assert booked.blocked_until - booked.end == timedelta(minutes=30)
    assert min(agenda.free_slots('Lomé', 1)) >= at(in_days(0), 0) + timedelta(hours=72)
    appointment = agenda.book(agenda.BookingRequest(
        requester_id=make_user(role='hote').pk, city='Lomé', start=at(in_days(5), 9),
        targets=[agenda.Target(id='x', title='Studio')]))
    assert appointment.end - appointment.start == timedelta(minutes=90)
    assert appointment.blocked_until - appointment.end == timedelta(hours=1)
    assert AppointmentModel.objects.count() == 2


def test_a_super_admin_grants_the_permission(super_admin, make_user, client_for):
    admin = make_user(role='admin')
    response = client_for(super_admin).patch(f'/api/v1/admin/users/{admin.pk}/',
                                             {'admin_permissions': ['agenda_settings']}, format='json')
    assert response.status_code == 200 and response.data['admin_permissions'] == ['agenda_settings']
    admin.refresh_from_db()
    rights = client_for(admin).get('/api/v1/admin/droits/').data
    assert rights['permissions'] == ['agenda_settings']
    other = make_user(role='admin')
    refused = client_for(admin).patch(f'/api/v1/admin/users/{other.pk}/', {'admin_permissions': ['agenda_settings']},
                                      format='json')
    assert refused.status_code == 403
    assert client_for(super_admin).patch(f'/api/v1/admin/users/{admin.pk}/', {'admin_permissions': ['nope']},
                                         format='json').status_code == 400


def test_super_admins_have_every_permission(super_admin, client_for):
    assert set(client_for(super_admin).get('/api/v1/admin/droits/').data['permissions']) == {
        'agenda_settings', 'validate_without_visit', 'activity_log'}
