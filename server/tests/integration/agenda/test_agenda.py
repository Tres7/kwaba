import uuid
from datetime import timedelta

import pytest
from django.core import mail
from django.db import IntegrityError, transaction

from apps.agenda import api as agenda
from apps.agenda.infrastructure.container import agenda_service
from apps.agenda.models import AgendaModel, AppointmentModel, DigestModel

from .conftest import at, in_days

AVAILABILITY = '/api/v1/agenda/availability/'
APPOINTMENTS = '/api/v1/agenda/appointments/'


@pytest.fixture
def agent(make_user):
    return make_user(role='agent')


@pytest.fixture
def host(make_user):
    return make_user(role='hote')


def _run():
    return agenda_service().run()


def _request(host, start, *targets, city='Lomé'):
    return agenda.BookingRequest(requester_id=host.pk, city=city, start=start,
                                 targets=list(targets) or [agenda.Target(id=str(uuid.uuid4()), title='Studio')])


class TestDatabaseGuarantees:
    def test_two_overlapping_appointments_are_refused_by_the_database(self, agent, make_agenda, make_appointment):
        calendar = make_agenda(agent)
        make_appointment(calendar, at(in_days(3), 9))
        with pytest.raises(IntegrityError, match='agenda_appointment_no_overlap'), transaction.atomic():
            make_appointment(calendar, at(in_days(3), 10))

    def test_the_margin_is_part_of_the_blocked_range(self, agent, make_agenda, make_appointment):
        calendar = make_agenda(agent)
        make_appointment(calendar, at(in_days(3), 9))
        make_appointment(calendar, at(in_days(3), 10, 30))

    def test_a_cancelled_appointment_frees_the_range(self, agent, make_agenda, make_appointment):
        calendar = make_agenda(agent)
        make_appointment(calendar, at(in_days(3), 9), status='cancelled')
        make_appointment(calendar, at(in_days(3), 9))

    def test_two_agents_can_visit_at_the_same_time(self, make_user, make_agenda, make_appointment):
        make_appointment(make_agenda(make_user(role='agent')), at(in_days(3), 9))
        make_appointment(make_agenda(make_user(role='agent')), at(in_days(3), 9))


class TestBooking:
    def test_the_least_busy_agent_gets_the_visit(self, make_user, make_agenda, make_appointment, host,
                                                 django_capture_on_commit_callbacks):
        busy, quiet = make_user(role='agent'), make_user(role='agent')
        make_appointment(make_agenda(busy), at(in_days(3), 14))
        make_agenda(quiet)
        with django_capture_on_commit_callbacks(execute=True):
            appointment = agenda.book(_request(host, at(in_days(3), 9)))
        assert appointment.agent_id == quiet.pk
        assert appointment.end - appointment.start == timedelta(minutes=60)
        assert appointment.blocked_until - appointment.end == timedelta(minutes=30)
        subjects = {m.to[0]: m.subject for m in mail.outbox}
        assert set(subjects) == {host.email, quiet.email}
        assert 'Visite confirmée' in subjects[host.email] and 'Nouvelle visite' in subjects[quiet.email]

    def test_the_same_slot_cannot_be_taken_twice(self, agent, make_agenda, host, make_user):
        make_agenda(agent)
        agenda.book(_request(host, at(in_days(3), 9)))
        with pytest.raises(agenda.AgendaError) as refused:
            agenda.book(_request(make_user(role='hote'), at(in_days(3), 9, 30)))
        assert refused.value.code == 409

    def test_a_listing_is_booked_only_once(self, make_user, make_agenda, host):
        make_agenda(make_user(role='agent'))
        make_agenda(make_user(role='agent'))
        target = agenda.Target(id='listing-1', title='Studio')
        agenda.book(_request(host, at(in_days(3), 9), target))
        with pytest.raises(agenda.AgendaError, match='déjà prévue'):
            agenda.book(_request(host, at(in_days(4), 9), target))

    def test_four_visits_a_day_then_the_agent_raises_the_limit(self, agent, make_agenda, make_appointment, host,
                                                                 client_for):
        calendar = make_agenda(agent)
        day = in_days(3)
        for hour in (8, 10, 12, 14):
            make_appointment(calendar, at(day, hour))
        with pytest.raises(agenda.AgendaError):
            agenda.book(_request(host, at(day, 16)))
        response = client_for(agent).put(f'{AVAILABILITY}day-limits/{day}/', {'max_visits': 5}, format='json')
        assert response.status_code == 200
        assert response.data['day_limits'] == [{'day': day, 'max_visits': 5}]
        agenda.book(_request(host, at(day, 16)))

    def test_no_agent_in_the_city(self, agent, make_agenda, host):
        make_agenda(agent, cities=['Kara'])
        with pytest.raises(agenda.AgendaError, match='Aucun agent'):
            agenda.book(_request(host, at(in_days(3), 9)))

    def test_an_inactive_agent_offers_no_slot(self, agent, make_agenda):
        make_agenda(agent)
        agent.is_active = False
        agent.save(update_fields=['is_active'])
        assert agenda.free_slots('Lomé', 1) == []

    def test_free_slots_merge_all_the_agents_of_the_city(self, make_user, make_agenda, make_appointment):
        first, second = make_agenda(make_user(role='agent')), make_agenda(make_user(role='agent'))
        make_appointment(first, at(in_days(3), 9))
        assert at(in_days(3), 9) in agenda.free_slots('lome', 1)
        make_appointment(second, at(in_days(3), 9))
        assert at(in_days(3), 9) not in agenda.free_slots('Lomé', 1)

    def test_removing_availability_never_cancels_an_appointment(self, agent, make_agenda, make_appointment,
                                                                client_for):
        appointment = make_appointment(make_agenda(agent), at(in_days(3), 9))
        assert client_for(agent).put(AVAILABILITY, {'cities': [], 'weekly_slots': []},
                                     format='json').status_code == 200
        appointment.refresh_from_db()
        assert appointment.status == 'confirmed'


class TestAvailabilityScreens:
    def test_week_cities_and_exceptions(self, agent, client_for):
        client = client_for(agent)
        response = client.put(AVAILABILITY, {
            'cities': ['Lomé', 'lome', ' Agbodrafo '],
            'weekly_slots': [{'weekday': 0, 'start': '08:00', 'end': '12:00'}],
        }, format='json')
        assert response.status_code == 200
        assert response.data['cities'] == ['Lomé', 'Agbodrafo']
        assert response.data['weekly_slots'] == [{'weekday': 0, 'start': '08:00', 'end': '12:00'}]
        assert response.data['rules']['max_per_day'] == 4
        day = in_days(5)
        created = client.post(f'{AVAILABILITY}exceptions/', {'day': str(day), 'kind': 'block'}, format='json')
        assert created.status_code == 201
        exception_id = created.data['exceptions'][0]['id']
        assert client.delete(f'{AVAILABILITY}exceptions/{exception_id}/').data['exceptions'] == []

    @pytest.mark.parametrize('body', [
        {'weekly_slots': [{'weekday': 0, 'start': '12:00', 'end': '08:00'}]},
        {'weekly_slots': [{'weekday': 9, 'start': '08:00', 'end': '12:00'}]},
        {'weekly_slots': [{'weekday': 0, 'start': 'midi'}]},
    ])
    def test_invalid_week(self, agent, client_for, body):
        assert client_for(agent).put(AVAILABILITY, body, format='json').status_code == 400

    def test_invalid_exceptions(self, agent, client_for):
        client = client_for(agent)
        url = f'{AVAILABILITY}exceptions/'
        assert client.post(url, {'day': str(in_days(-1)), 'kind': 'block'}, format='json').status_code == 400
        assert client.post(url, {'day': str(in_days(2)), 'kind': 'extra'}, format='json').status_code == 400
        assert client.post(url, {'day': str(in_days(2)), 'kind': 'other'}, format='json').status_code == 400

    def test_day_limit_is_bounded(self, agent, client_for):
        url = f'{AVAILABILITY}day-limits/{in_days(2)}/'
        assert client_for(agent).put(url, {'max_visits': 11}, format='json').status_code == 400

    def test_only_agents_and_admins(self, make_user, client_for, api_client):
        assert api_client.get(AVAILABILITY).status_code == 401
        assert client_for(make_user(role='hote')).get(AVAILABILITY).status_code == 403
        assert client_for(make_user(role='admin')).get(AVAILABILITY).status_code == 200


class TestAgentAgenda:
    def test_the_agent_sees_only_their_appointments(self, agent, make_user, make_agenda, make_appointment,
                                                    client_for):
        mine = make_appointment(make_agenda(agent), at(in_days(3), 9))
        make_appointment(make_agenda(make_user(role='agent')), at(in_days(3), 9))
        params = {'start': str(in_days(0)), 'end': str(in_days(6))}
        results = client_for(agent).get(APPOINTMENTS, params).data['results']
        assert [r['id'] for r in results] == [str(mine.id)]
        assert results[0]['title'] == 'Studio meublé' and results[0]['agent'] is None

    def test_an_admin_sees_every_agent(self, make_user, make_agenda, make_appointment, client_for):
        for _ in range(2):
            make_appointment(make_agenda(make_user(role='agent')), at(in_days(3), 9))
        params = {'start': str(in_days(0)), 'end': str(in_days(6)), 'agent': 'all'}
        results = client_for(make_user(role='admin')).get(APPOINTMENTS, params).data['results']
        assert len(results) == 2 and all(r['agent']['name'] for r in results)

    def test_period_is_bounded(self, agent, client_for):
        client = client_for(agent)
        assert client.get(APPOINTMENTS, {'start': 'hier'}).status_code == 400
        assert client.get(APPOINTMENTS, {'start': str(in_days(0)), 'end': str(in_days(90))}).status_code == 400

    def test_detail_gives_the_host_contact_to_the_agent_only(self, agent, make_user, make_agenda, make_appointment,
                                                            client_for, host):
        appointment = make_appointment(make_agenda(agent), at(in_days(3), 9), requester=host, address='Bè Kpota')
        detail = client_for(agent).get(f'{APPOINTMENTS}{appointment.id}/').data
        assert detail['host']['phone'] == host.phone and detail['address'] == 'Bè Kpota'
        assert client_for(make_user(role='agent')).get(f'{APPOINTMENTS}{appointment.id}/').status_code == 404

    def test_on_the_way_tells_the_host_once(self, agent, make_agenda, make_appointment, client_for, host,
                                            frozen_clock, django_capture_on_commit_callbacks):
        appointment = make_appointment(make_agenda(agent), at(in_days(3), 9), requester=host)
        url = f'{APPOINTMENTS}{appointment.id}/on-the-way/'
        assert client_for(agent).post(url).status_code == 403
        frozen_clock(at(in_days(3), 8, 30))
        with django_capture_on_commit_callbacks(execute=True):
            assert client_for(agent).post(url).status_code == 200
            assert client_for(agent).post(url).status_code == 200
        assert [m.subject for m in mail.outbox] == ["L'agent Kwa-Ba est en route"]


class TestCalendarFiles:
    def test_one_visit_file_has_only_the_name_and_the_city(self, agent, make_agenda, make_appointment, client_for,
                                                           host):
        appointment = make_appointment(make_agenda(agent), at(in_days(3), 9), requester=host, address='Bè Kpota')
        response = client_for(agent).get(f'{APPOINTMENTS}{appointment.id}/ics/')
        content = response.content.decode().replace('\r\n ', '')
        assert response['Content-Type'] == 'text/calendar; charset=utf-8'
        assert 'SUMMARY:Visite · Studio meublé' in content and 'LOCATION:Lomé' in content
        assert 'Bè Kpota' not in content and host.phone not in content and host.email not in content

    def test_private_feed_is_revocable(self, agent, make_agenda, make_appointment, client_for, api_client):
        calendar = make_agenda(agent)
        make_appointment(calendar, at(in_days(3), 9))
        make_appointment(calendar, at(in_days(3), 14), status='cancelled', sequence=1)
        url = client_for(agent).get('/api/v1/agenda/feed/').data['url']
        token = url.rstrip('/').rsplit('/', 1)[-1]
        content = api_client.get(f'/api/v1/agenda/feed/{token}/').content.decode()
        assert content.count('BEGIN:VEVENT') == 2 and 'STATUS:CANCELLED' in content
        client_for(agent).post('/api/v1/agenda/feed/')
        assert api_client.get(f'/api/v1/agenda/feed/{token}/').status_code == 404

    def test_feed_of_an_inactive_agent_is_closed(self, agent, make_agenda, api_client):
        token = make_agenda(agent).ics_token
        agent.is_active = False
        agent.save(update_fields=['is_active'])
        assert api_client.get(f'/api/v1/agenda/feed/{token}/').status_code == 404


class TestWorker:
    def test_evening_digest_once_per_agent_and_host_reminder(self, agent, make_agenda, make_appointment, host,
                                                             frozen_clock, django_capture_on_commit_callbacks):
        calendar = make_agenda(agent)
        day = in_days(3)
        make_appointment(calendar, at(day, 14), requester=host, targets=[{'id': 'b', 'title': 'Villa'}])
        make_appointment(calendar, at(day, 9), requester=host, targets=[{'id': 'a', 'title': 'Studio'}])
        make_appointment(calendar, at(day, 11), status='cancelled', targets=[{'id': 'c', 'title': 'Annulée'}])
        frozen_clock(at(day - timedelta(days=1), 17))
        with django_capture_on_commit_callbacks(execute=True):
            _run()
        assert mail.outbox == []
        frozen_clock(at(day - timedelta(days=1), 18, 5))
        with django_capture_on_commit_callbacks(execute=True):
            _run()
            _run()
        digests = [m for m in mail.outbox if m.to == [agent.email]]
        assert len(digests) == 1 and 'demain (2)' in digests[0].subject
        body = digests[0].body
        assert body.index('9 h') < body.index('14 h') and 'Annulée' not in body
        assert len([m for m in mail.outbox if m.to == [host.email]]) == 2
        assert DigestModel.objects.count() == 1

    def test_agent_without_availability_is_reminded_weekly(self, agent, frozen_clock,
                                                           django_capture_on_commit_callbacks):
        frozen_clock(at(in_days(0), 10))
        with django_capture_on_commit_callbacks(execute=True):
            _run()
            _run()
        assert [m.to for m in mail.outbox] == [[agent.email]]
        frozen_clock(at(in_days(8), 10))
        with django_capture_on_commit_callbacks(execute=True):
            _run()
        assert len(mail.outbox) == 2

    def test_visit_without_decision_alerts_the_admins_once(self, agent, make_user, make_agenda, make_appointment,
                                                           frozen_clock, django_capture_on_commit_callbacks):
        admin = make_user(role='admin')
        appointment = make_appointment(make_agenda(agent), at(in_days(3), 9))
        frozen_clock(at(in_days(3), 13))
        with django_capture_on_commit_callbacks(execute=True):
            _run()
            _run()
        alerts = [m for m in mail.outbox if m.to == [admin.email]]
        assert len(alerts) == 1 and 'sans décision' in alerts[0].subject
        appointment.refresh_from_db()
        assert appointment.alert_at is not None


class TestAdminViews:
    def test_coverage_and_delays(self, make_user, make_agenda, make_appointment, client_for):
        admin = make_user(role='admin')
        make_appointment(make_agenda(make_user(role='agent'), cities=['Lomé', 'Kpalimé']), at(in_days(3), 9))
        data = client_for(admin).get('/api/v1/agenda/admin/coverage/').data
        cities = {row['city']: row for row in data['cities']}
        assert set(cities) == {'Lomé', 'Kpalimé'}
        assert cities['Lomé']['upcoming_visits'] == 1 and cities['Lomé']['free_slots'] > 0
        assert data['delays']['total'] == 1

    def test_agents_cannot_see_the_admin_views(self, agent, client_for):
        assert client_for(agent).get('/api/v1/agenda/admin/coverage/').status_code == 403
        assert client_for(agent).get('/api/v1/agenda/admin/agents/').status_code == 403


def test_agenda_table_is_created_lazily(agent, client_for):
    assert not AgendaModel.objects.exists()
    client_for(agent).get(AVAILABILITY)
    assert AgendaModel.objects.get().agent_id == agent.pk
    assert AppointmentModel.objects.count() == 0


def test_worker_command_runs_one_pass(agent, monkeypatch, django_capture_on_commit_callbacks):
    from django.core.management import call_command

    monkeypatch.setattr('apps.agenda.management.commands.agenda_worker.close_old_connections', lambda: None)
    with django_capture_on_commit_callbacks(execute=True):
        call_command('agenda_worker', '--once')
    assert [m.to for m in mail.outbox] == [[agent.email]]


class TestTargetAppointment:
    def test_planned_visit_of_a_listing(self, agent, make_user, make_agenda, make_appointment, client_for):
        appointment = make_appointment(make_agenda(agent), at(in_days(3), 9),
                                       targets=[{'id': 'listing-9', 'title': 'Villa'}])
        mine = client_for(agent).get('/api/v1/agenda/appointments/for-target/listing-9/').data['appointment']
        assert mine['id'] == str(appointment.id) and mine['mine'] is True and mine['origin'] == 'host'
        other = client_for(make_user(role='agent')).get('/api/v1/agenda/appointments/for-target/listing-9/')
        assert other.data['appointment']['mine'] is False and other.data['appointment']['agent']['name']

    def test_no_planned_visit(self, agent, make_agenda, make_appointment, client_for):
        make_appointment(make_agenda(agent), at(in_days(3), 9), status='cancelled',
                         targets=[{'id': 'listing-9', 'title': 'Villa'}])
        assert client_for(agent).get('/api/v1/agenda/appointments/for-target/listing-9/').data == {'appointment': None}

    def test_reserved_to_agents(self, make_user, client_for):
        assert client_for(make_user(role='hote')).get('/api/v1/agenda/appointments/for-target/x/').status_code == 403
