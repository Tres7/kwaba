import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from django.core import mail

from apps.agenda.models import AgendaModel, AppointmentModel, WeeklySlotModel
from apps.terrain.models import MissionModel
from apps.verifications.appointments import remind_hosts
from apps.verifications.models import PieceIdentiteModel, VisitInvitationModel

VISIT = '/api/v1/verifications/visit/'
TOUT_CONFORME = {'identite': True, 'adresse': True, 'photos': True, 'equipements': True}


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=timezone.utc)


def in_days(days: int) -> date:
    return (datetime.now(timezone.utc) + timedelta(days=days)).date()


@pytest.fixture
def frozen_now(monkeypatch):
    def _freeze(moment: datetime):
        monkeypatch.setattr('django.utils.timezone.now', lambda: moment)

    return _freeze


@pytest.fixture
def host(make_user):
    host = make_user(role='hote')
    PieceIdentiteModel.objects.create(hote_id=host.pk, type_piece='cni', statut='verifiee')
    return host


@pytest.fixture
def make_listing(make_hebergement, host):
    def _make(name='Studio meublé', latitude='6.130000', longitude='1.220000', **fields):
        return make_hebergement(host=host, name=name, statut_verification='en_attente', city='Lomé',
                                location='Bè Kpota', latitude=Decimal(latitude), longitude=Decimal(longitude),
                                **fields)

    return _make


@pytest.fixture
def make_agent(make_user):
    def _make(cities=('Lomé',)):
        agent = make_user(role='agent')
        agenda = AgendaModel.objects.create(agent_id=agent.pk, cities=list(cities))
        WeeklySlotModel.objects.bulk_create(
            [WeeklySlotModel(agenda=agenda, weekday=d, start=time(8), end=time(18)) for d in range(7)])
        return agent

    return _make


def _book(client, listings, start):
    return client.post(f'{VISIT}book/', {'listings': [str(x.id) for x in listings], 'start': start.isoformat()},
                       format='json')


def _mission(listing):
    return MissionModel.objects.filter(type='logement', cible=str(listing.id), statut='en_cours').first()


class TestHostBooking:
    def test_the_host_sees_slots_without_agent_names_and_books(self, client_for, host, make_listing, make_agent,
                                                               django_capture_on_commit_callbacks):
        listing = make_listing()
        agent = make_agent()
        client = client_for(host)
        data = client.get(VISIT).data
        assert [x['id'] for x in data['listings']] == [str(listing.id)]
        assert data['listings'][0]['appointment'] is None
        slots = client.get(f'{VISIT}slots/', {'listings': str(listing.id)}).data['slots']
        assert at(in_days(3), 9) in slots
        with django_capture_on_commit_callbacks(execute=True):
            response = _book(client, [listing], at(in_days(3), 9))
        assert response.status_code == 201
        assert 'agent' not in json.dumps(response.data, default=str).replace('agent_id', '')
        assert response.data['movable'] is True
        assert _mission(listing).agent_id == agent.pk
        assert client.get(VISIT).data['listings'][0]['appointment']['id'] == response.data['id']
        assert [m.to for m in mail.outbox] == [[host.email]]

    def test_a_second_host_cannot_take_the_same_slot(self, client_for, host, make_listing, make_agent, make_user,
                                                      make_hebergement):
        make_agent()
        assert _book(client_for(host), [make_listing()], at(in_days(3), 9)).status_code == 201
        other = make_user(role='hote')
        PieceIdentiteModel.objects.create(hote_id=other.pk, type_piece='cni', statut='verifiee')
        other_listing = make_hebergement(host=other, statut_verification='en_attente', city='Lomé')
        response = _book(client_for(other), [other_listing], at(in_days(3), 9))
        assert response.status_code == 409

    def test_notice_of_twenty_four_hours(self, client_for, host, make_listing, make_agent):
        make_agent()
        soon = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=3)
        response = _book(client_for(host), [make_listing()], soon)
        assert response.status_code == 409 and '24 h' in response.data['detail']

    def test_same_site_group_takes_one_longer_slot(self, client_for, host, make_listing, make_agent):
        make_agent()
        rooms = [make_listing(name=f'Chambre {i}', latitude=f'6.13{i}000') for i in range(1, 3)]
        response = _book(client_for(host), rooms, at(in_days(3), 9))
        assert response.status_code == 201
        appointment = AppointmentModel.objects.get()
        assert appointment.end - appointment.start == timedelta(minutes=80)
        assert all(_mission(room) for room in rooms)

    def test_listings_too_far_apart_cannot_be_grouped(self, client_for, host, make_listing, make_agent):
        make_agent()
        far = [make_listing(name='Ici'), make_listing(name='Là-bas', latitude='6.200000')]
        response = _book(client_for(host), far, at(in_days(3), 9))
        assert response.status_code == 400 and 'même site' in response.data['detail']

    def test_a_host_cannot_book_someone_elses_listing(self, client_for, make_user, make_listing, make_agent):
        make_agent()
        stranger = make_user(role='hote')
        response = _book(client_for(stranger), [make_listing()], at(in_days(3), 9))
        assert response.status_code == 404

    def test_a_listing_already_taken_by_an_agent_shows_only_their_slots(self, client_for, host, make_listing,
                                                                         make_agent, make_user):
        listing = make_listing()
        first, second = make_agent(), make_agent()
        MissionModel.objects.create(type='logement', cible=str(listing.id), agent_id=second.pk, titre='x')
        AppointmentModel.objects.create(
            agenda=AgendaModel.objects.get(agent_id=second.pk), agent_id=second.pk, requester_id=make_user().pk,
            targets=[{'id': 'other', 'title': 'x'}], city='Lomé', start=at(in_days(3), 9),
            end=at(in_days(3), 10), blocked_until=at(in_days(3), 10, 30), created_at=datetime.now(timezone.utc))
        slots = client_for(host).get(f'{VISIT}slots/', {'listings': str(listing.id)}).data['slots']
        assert at(in_days(3), 9) not in slots
        response = _book(client_for(host), [listing], at(in_days(3), 11))
        assert response.status_code == 201 and response.data['agent_id'] == str(second.pk)
        assert first.pk != second.pk

    def test_only_hosts(self, client_for, make_user, api_client):
        assert api_client.get(VISIT).status_code == 401
        assert client_for(make_user()).get(VISIT).status_code == 403


class TestMoveAndCancel:
    def test_the_host_moves_until_twenty_four_hours_before(self, client_for, host, make_listing, make_agent,
                                                           frozen_now, django_capture_on_commit_callbacks):
        make_agent()
        client = client_for(host)
        appointment_id = _book(client, [make_listing()], at(in_days(3), 9)).data['id']
        slots = client.get(f'{VISIT}appointments/{appointment_id}/slots/').data['slots']
        assert at(in_days(3), 9, 30) in slots
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(f'{VISIT}appointments/{appointment_id}/move/',
                                   {'start': at(in_days(4), 15).isoformat()}, format='json')
        assert response.status_code == 200 and response.data['start'] == at(in_days(4), 15)
        assert 'déplacée' in mail.outbox[-1].subject
        frozen_now(at(in_days(4), 0))
        late = client.post(f'{VISIT}appointments/{appointment_id}/move/', {'start': at(in_days(5), 9).isoformat()},
                           format='json')
        assert late.status_code == 403

    def test_the_agent_cancels_with_a_reason_and_the_listing_goes_back_to_the_queue(
            self, client_for, host, make_listing, make_agent, django_capture_on_commit_callbacks):
        agent = make_agent()
        listing = make_listing()
        appointment_id = _book(client_for(host), [listing], at(in_days(3), 9)).data['id']
        url = f'/api/v1/verifications/appointments/{appointment_id}/cancel/'
        assert client_for(agent).post(url, {'reason': ''}, format='json').status_code == 400
        with django_capture_on_commit_callbacks(execute=True):
            response = client_for(agent).post(url, {'reason': 'Agent malade'}, format='json')
        assert response.status_code == 200 and response.data['status'] == 'cancelled'
        assert _mission(listing) is None
        assert 'annulée' in mail.outbox[-1].subject and 'Agent malade' in mail.outbox[-1].body
        assert client_for(host).get(VISIT).data['listings'][0]['appointment'] is None

    def test_another_agent_cannot_cancel(self, client_for, host, make_listing, make_agent):
        make_agent()
        appointment_id = _book(client_for(host), [make_listing()], at(in_days(3), 9)).data['id']
        response = client_for(make_agent()).post(f'/api/v1/verifications/appointments/{appointment_id}/cancel/',
                                                 {'reason': 'Pas dispo'}, format='json')
        assert response.status_code == 403


class TestAgentAndAdmin:
    def test_phone_booking_skips_availability_and_is_marked(self, client_for, make_listing, make_agent,
                                                            django_capture_on_commit_callbacks):
        listing = make_listing()
        agent = make_agent(cities=['Kara'])
        start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=5)
        with django_capture_on_commit_callbacks(execute=True):
            response = client_for(agent).post(f'/api/v1/verifications/listings/{listing.id}/appointment/',
                                              {'start': start.isoformat()}, format='json')
        assert response.status_code == 201 and response.data['origin'] == 'phone'
        assert _mission(listing).agent_id == agent.pk
        assert 'Comme convenu par téléphone' in mail.outbox[-1].body

    def test_admin_reassigns_to_another_agent(self, client_for, host, make_listing, make_agent, make_user):
        listing = make_listing()
        first = make_agent()
        appointment_id = _book(client_for(host), [listing], at(in_days(3), 9)).data['id']
        second = make_agent()
        admin = make_user(role='admin')
        url = f'/api/v1/verifications/appointments/{appointment_id}/reassign/'
        assert client_for(first).post(url, {'agent_id': str(second.pk)}, format='json').status_code == 403
        response = client_for(admin).post(url, {'agent_id': str(second.pk)}, format='json')
        assert response.status_code == 200 and response.data['agent_id'] == str(second.pk)
        assert _mission(listing).agent_id == second.pk

    def test_the_decision_marks_the_visit_done(self, client_for, host, make_listing, make_agent):
        agent = make_agent()
        listing = make_listing()
        _book(client_for(host), [listing], at(in_days(3), 9))
        decision = client_for(agent).post(f'/api/v1/verifications/visites/{listing.id}/decision/',
                                          {'decision': 'validee', 'controles': json.dumps(TOUT_CONFORME)},
                                          format='multipart')
        assert decision.status_code == 201
        assert AppointmentModel.objects.get().status == 'done'


class TestHostReminders:
    def test_reminder_at_two_days_then_admin_alert_at_three(self, host, make_listing, make_user, frozen_now,
                                                           django_capture_on_commit_callbacks):
        admin = make_user(role='admin')
        listing = make_listing()
        VisitInvitationModel.objects.create(listing_id=listing.id, host_id=host.pk,
                                            invited_at=datetime.now(timezone.utc))
        frozen_now(datetime.now(timezone.utc) + timedelta(days=2, hours=1))
        with django_capture_on_commit_callbacks(execute=True):
            assert remind_hosts() == {'host_reminders': 1, 'host_alerts': 0}
            assert remind_hosts() == {'host_reminders': 0, 'host_alerts': 0}
        assert [m.to for m in mail.outbox] == [[host.email]]
        frozen_now(datetime.now(timezone.utc) + timedelta(days=3, hours=1))
        with django_capture_on_commit_callbacks(execute=True):
            assert remind_hosts() == {'host_reminders': 0, 'host_alerts': 1}
        alert = mail.outbox[-1]
        assert alert.to == [admin.email] and listing.name in alert.body and 'Lomé' in alert.body

    def test_no_reminder_once_booked(self, client_for, host, make_listing, make_agent, frozen_now):
        make_agent()
        listing = make_listing()
        VisitInvitationModel.objects.create(listing_id=listing.id, host_id=host.pk,
                                            invited_at=datetime.now(timezone.utc) - timedelta(days=4))
        _book(client_for(host), [listing], at(in_days(3), 9))
        assert remind_hosts() == {'host_reminders': 0, 'host_alerts': 0}
