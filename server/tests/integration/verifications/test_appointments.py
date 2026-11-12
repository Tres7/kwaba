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


def listing_host_email(listing):
    from apps.users.infrastructure.persistence.models import UserModel
    return UserModel.objects.get(pk=listing.host_id).email


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
        assert sorted(m.to[0] for m in mail.outbox) == sorted([host.email, agent.email])
        to_agent, = [m for m in mail.outbox if m.to == [agent.email]]
        assert 'Nouvelle visite' in to_agent.subject and 'Studio meublé' in to_agent.body

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
        agent = make_agent()
        client = client_for(host)
        appointment_id = _book(client, [make_listing()], at(in_days(3), 9)).data['id']
        slots = client.get(f'{VISIT}appointments/{appointment_id}/slots/').data['slots']
        assert at(in_days(3), 9, 30) in slots
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(f'{VISIT}appointments/{appointment_id}/move/',
                                   {'start': at(in_days(4), 15).isoformat()}, format='json')
        assert response.status_code == 200 and response.data['start'] == at(in_days(4), 15)
        assert sorted(m.to[0] for m in mail.outbox if 'déplacée' in m.subject) == sorted([host.email, agent.email])
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
        assert [m.to for m in mail.outbox] == [[listing_host_email(listing)]]
        assert 'Comme convenu par téléphone' in mail.outbox[-1].body

    def test_admin_reassigns_to_another_agent(self, client_for, host, make_listing, make_agent, make_user,
                                              django_capture_on_commit_callbacks):
        listing = make_listing()
        first = make_agent()
        appointment_id = _book(client_for(host), [listing], at(in_days(3), 9)).data['id']
        second = make_agent()
        admin = make_user(role='admin')
        url = f'/api/v1/verifications/appointments/{appointment_id}/reassign/'
        assert client_for(first).post(url, {'agent_id': str(second.pk)}, format='json').status_code == 403
        with django_capture_on_commit_callbacks(execute=True):
            response = client_for(admin).post(url, {'agent_id': str(second.pk)}, format='json')
        assert response.status_code == 200 and response.data['agent_id'] == str(second.pk)
        assert _mission(listing).agent_id == second.pk
        subjects = {m.to[0]: m.subject for m in mail.outbox}
        assert 'Nouvelle visite' in subjects[second.email] and 'autre agent' in subjects[first.email]
        assert host.email not in subjects

    def test_deciding_before_the_visit_needs_a_reason_and_frees_the_slot(self, client_for, host, make_listing,
                                                                          make_agent):
        agent = make_agent()
        listing = make_listing()
        _book(client_for(host), [listing], at(in_days(3), 9))
        mission = client_for(agent).get(f'/api/v1/agent/missions/logement/{listing.id}/').data
        assert mission['early_visit']['start'] == at(in_days(3), 9)
        url = f'/api/v1/verifications/visites/{listing.id}/decision/'
        body = {'decision': 'validee', 'controles': json.dumps(TOUT_CONFORME)}
        refused = client_for(agent).post(url, body, format='multipart')
        assert refused.status_code == 400 and 'prévue' in refused.data['detail']
        decision = client_for(agent).post(url, {**body, 'early_reason': "Visite faite plus tôt avec l'hôte"},
                                          format='multipart')
        assert decision.status_code == 201
        appointment = AppointmentModel.objects.get()
        assert appointment.status == 'done' and appointment.closing_reason == "Visite faite plus tôt avec l'hôte"
        assert at(in_days(3), 9) in client_for(host).get(
            f'{VISIT}slots/', {'listings': str(make_listing(name='Autre').id)}).data['slots']

    def test_a_group_visit_is_kept_while_another_listing_waits(self, client_for, host, make_listing, make_agent):
        agent = make_agent()
        rooms = [make_listing(name=f'Chambre {i}', latitude=f'6.13{i}000') for i in range(1, 3)]
        _book(client_for(host), rooms, at(in_days(3), 9))
        assert client_for(agent).get(f'/api/v1/agent/missions/logement/{rooms[0].id}/').data['early_visit'] is None
        decision = client_for(agent).post(f'/api/v1/verifications/visites/{rooms[0].id}/decision/',
                                          {'decision': 'validee', 'controles': json.dumps(TOUT_CONFORME)},
                                          format='multipart')
        assert decision.status_code == 201
        assert AppointmentModel.objects.get().status == 'confirmed'

    def test_the_decision_after_the_visit_closes_it_without_reason(self, client_for, host, make_listing,
                                                                  make_agent, frozen_now):
        agent = make_agent()
        listing = make_listing()
        _book(client_for(host), [listing], at(in_days(3), 9))
        frozen_now(at(in_days(3), 10, 15))
        decision = client_for(agent).post(f'/api/v1/verifications/visites/{listing.id}/decision/',
                                          {'decision': 'validee', 'controles': json.dumps(TOUT_CONFORME)},
                                          format='multipart')
        assert decision.status_code == 201
        appointment = AppointmentModel.objects.get()
        assert appointment.status == 'done' and appointment.closing_reason == ''


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


class TestValidationWithoutVisit:
    @pytest.fixture
    def super_admin(self, make_user):
        return make_user(role='admin', is_superuser=True, is_staff=True)

    def _validate(self, client, listing, keep_visit=False):
        return client.patch(f'/api/v1/admin/hebergements/{listing.id}/',
                            {'est_verifie': True, 'motif': 'Hôtel déjà connu de l\'équipe', 'keep_visit': keep_visit},
                            format='json')

    def test_the_planned_visit_is_cancelled_and_both_are_told_once(self, client_for, host, make_listing, make_agent,
                                                                   super_admin, django_capture_on_commit_callbacks):
        agent = make_agent()
        listing = make_listing()
        _book(client_for(host), [listing], at(in_days(3), 9))
        mail.outbox.clear()
        with django_capture_on_commit_callbacks(execute=True):
            assert self._validate(client_for(super_admin), listing).status_code == 200
        appointment = AppointmentModel.objects.get()
        assert appointment.status == 'cancelled' and appointment.cancelled_by == 'admin'
        assert _mission(listing) is None
        assert MissionModel.objects.get(cible=str(listing.id)).statut == 'terminee'
        to_host = [m for m in mail.outbox if m.to == [host.email]]
        to_agent = [m for m in mail.outbox if m.to == [agent.email]]
        assert len(to_host) == 1 and "n'a plus lieu" in to_host[0].body
        assert len(to_agent) == 1 and 'annulée' in to_agent[0].body and "Hôtel déjà connu" in to_agent[0].body
        assert at(in_days(3), 9) in client_for(host).get(
            f'{VISIT}slots/', {'listings': str(make_listing(name='Autre').id)}).data['slots']

    def test_kept_visit_becomes_a_post_check(self, client_for, host, make_listing, make_agent, super_admin,
                                             django_capture_on_commit_callbacks):
        agent = make_agent()
        listing = make_listing()
        appointment_id = _book(client_for(host), [listing], at(in_days(3), 9)).data['id']
        mail.outbox.clear()
        with django_capture_on_commit_callbacks(execute=True):
            self._validate(client_for(super_admin), listing, keep_visit=True)
        appointment = AppointmentModel.objects.get()
        assert appointment.status == 'confirmed' and appointment.post_check
        assert 'contrôle a posteriori' in [m for m in mail.outbox if m.to == [agent.email]][0].body
        detail = client_for(agent).get(f'/api/v1/agenda/appointments/{appointment_id}/').data
        assert detail['post_check'] is True
        url = f'/api/v1/verifications/appointments/{appointment_id}/post-check/'
        assert client_for(make_agent()).post(url, {'compliant': True}, format='json').status_code == 403
        response = client_for(agent).post(url, {'compliant': True}, format='json')
        assert response.status_code == 200 and response.data['status'] == 'done'
        listing.refresh_from_db()
        assert listing.statut_verification == 'verifiee'

    def test_failed_post_check_unpublishes_and_alerts_the_admins(self, client_for, host, make_listing, make_agent,
                                                                 super_admin, frozen_now,
                                                                 django_capture_on_commit_callbacks):
        agent = make_agent()
        listing = make_listing()
        appointment_id = _book(client_for(host), [listing], at(in_days(3), 9)).data['id']
        self._validate(client_for(super_admin), listing, keep_visit=True)
        frozen_now(at(in_days(3), 9, 30))
        url = f'/api/v1/verifications/appointments/{appointment_id}/post-check/'
        assert client_for(agent).post(url, {'compliant': False, 'reason': 'court'}, format='json').status_code == 400
        mail.outbox.clear()
        with django_capture_on_commit_callbacks(execute=True):
            response = client_for(agent).post(url, {'compliant': False, 'reason': "Pas de piscine, photos d'un autre lieu"},
                                              format='json')
        assert response.status_code == 200
        listing.refresh_from_db()
        assert listing.statut_verification == 'refusee' and 'piscine' in listing.motif_refus
        assert AppointmentModel.objects.get().closing_reason.startswith('Contrôle non conforme')
        assert {m.to[0] for m in mail.outbox} == {host.email, super_admin.email}

    def test_a_shared_group_visit_is_kept_for_the_other_listings(self, client_for, host, make_listing, make_agent,
                                                                 super_admin):
        make_agent()
        rooms = [make_listing(name=f'Chambre {i}', latitude=f'6.13{i}000') for i in range(1, 3)]
        _book(client_for(host), rooms, at(in_days(3), 9))
        self._validate(client_for(super_admin), rooms[0])
        assert AppointmentModel.objects.get().status == 'confirmed'
        assert _mission(rooms[1]) is not None

    def test_without_the_permission(self, client_for, make_listing, make_user):
        response = self._validate(client_for(make_user(role='admin')), make_listing())
        assert response.status_code == 403
