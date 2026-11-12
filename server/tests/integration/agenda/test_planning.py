from datetime import time

import pytest

from apps.agenda.models import AvailabilityExceptionModel, DayLimitModel

from .conftest import at, in_days

URL = '/api/v1/admin/agenda/planning/'


@pytest.fixture
def admin(make_user):
    return make_user(role='admin')


def _agents(response) -> dict:
    return {a['name']: a for a in response.data['agents']}


def test_one_row_per_agent_with_windows_blocks_and_visits(admin, make_user, make_agenda, make_appointment,
                                                          client_for):
    day = in_days(3)
    kossi = make_user(role='agent', first_name='Kossi', last_name='Mensah')
    calendar = make_agenda(kossi, start=time(8), end=time(18))
    AvailabilityExceptionModel.objects.create(agenda=calendar, day=day, kind='block', start=time(12), end=time(14))
    DayLimitModel.objects.create(agenda=calendar, day=day, max_visits=5)
    make_appointment(calendar, at(day, 9), targets=[{'id': 'a', 'title': 'Villa'}], address='Bè Kpota')
    make_appointment(calendar, at(day, 15), status='cancelled', targets=[{'id': 'b', 'title': 'Studio'}])
    make_appointment(calendar, at(in_days(4), 9), targets=[{'id': 'c', 'title': 'Autre jour'}])
    afi = make_user(role='agent', first_name='Afi', last_name='Agbeko')
    make_agenda(afi, cities=['Kara'])
    away = make_user(role='agent', first_name='Ama', last_name='Conge')
    AvailabilityExceptionModel.objects.create(agenda=make_agenda(away), day=day, kind='block')
    make_user(role='agent', first_name='Sans', last_name='Agenda')

    response = client_for(admin).get(URL, {'day': str(day)})
    assert response.status_code == 200
    agents = _agents(response)
    assert set(agents) == {'Kossi Mensah', 'Afi Agbeko', 'Ama Conge', 'Sans Agenda'}
    kossi_row = agents['Kossi Mensah']
    assert kossi_row['windows'] == [{'start': at(day, 8), 'end': at(day, 12)}, {'start': at(day, 14), 'end': at(day, 18)}]
    assert kossi_row['blocks'] == [{'start': at(day, 12), 'end': at(day, 14)}]
    assert kossi_row['max_visits'] == 5 and kossi_row['visits'] == 1
    assert [a['title'] for a in kossi_row['appointments']] == ['Villa', 'Studio']
    assert kossi_row['appointments'][0]['address'] == 'Bè Kpota'
    assert agents['Ama Conge']['windows'] == [] and len(agents['Ama Conge']['blocks']) == 1
    assert agents['Sans Agenda']['windows'] == [] and agents['Sans Agenda']['cities'] == []
    assert response.data['cities'] == ['Kara', 'Lomé']


def test_filter_by_city(admin, make_user, make_agenda, client_for):
    make_agenda(make_user(role='agent', first_name='Kossi', last_name='Mensah'))
    make_agenda(make_user(role='agent', first_name='Afi', last_name='Agbeko'), cities=['Kara'])
    response = client_for(admin).get(URL, {'day': str(in_days(1)), 'city': 'kara'})
    assert list(_agents(response)) == ['Afi Agbeko']
    assert response.data['cities'] == ['Kara', 'Lomé']


def test_inactive_agents_are_left_out(admin, make_user, make_agenda, client_for):
    gone = make_user(role='agent', first_name='Parti', last_name='Agent', is_active=False)
    make_agenda(gone)
    assert 'Parti Agent' not in _agents(client_for(admin).get(URL, {'day': str(in_days(1))}))


def test_today_by_default_and_invalid_day(admin, client_for):
    client = client_for(admin)
    assert client.get(URL).status_code == 200
    assert client.get(URL, {'day': 'demain'}).status_code == 400


def test_reserved_to_admins_with_the_verifications_section(make_user, client_for):
    assert client_for(make_user(role='agent')).get(URL).status_code == 403
    assert client_for(make_user(role='admin', admin_sections=['avis'])).get(URL).status_code == 403
    assert client_for(make_user(role='admin', admin_sections=['verifications'])).get(URL).status_code == 200
