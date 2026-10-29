from datetime import timedelta

import pytest
from django.utils import timezone

from apps.hebergements.models import HebergementModel
from apps.messaging.infrastructure.persistence.models import ConversationModel
from apps.reservations.models import ReservationModel
from apps.securite.models import JournalAuditModel
from apps.verifications.models import VisiteModel

HEBERGEMENTS = '/api/v1/hebergements/'
ADMIN = '/api/v1/admin/hebergements/'

pytestmark = pytest.mark.django_db


@pytest.fixture
def annonce(make_hebergement):
    return make_hebergement()


def _supprimer(client_for, annonce):
    return client_for(annonce.host).delete(f'{HEBERGEMENTS}{annonce.id}/')


def test_deleting_archives_and_keeps_the_history(client_for, make_user, annonce, make_reservation):
    passee = make_reservation(annonce, starts_in=-10, nights=3)
    maintenant = timezone.now()
    conversation = ConversationModel.objects.create(hebergement_id=annonce.id, guest=make_user(), host=annonce.host,
                                                    created_at=maintenant, last_message_at=maintenant)
    visite = VisiteModel.objects.create(hebergement_id=annonce.id, decision='validee')

    assert _supprimer(client_for, annonce).status_code == 204

    archivee = HebergementModel.tous.get(pk=annonce.pk)
    assert archivee.archivee_le is not None and not archivee.is_available
    assert not HebergementModel.objects.filter(pk=annonce.pk).exists()
    assert ReservationModel.objects.filter(pk=passee.pk, status='confirmed').exists()
    assert ConversationModel.objects.filter(pk=conversation.pk).exists()
    assert VisiteModel.objects.filter(pk=visite.pk).exists()


def test_pending_bookings_are_cancelled_and_the_traveller_told(client_for, make_user, annonce, make_reservation,
                                                                mailoutbox, django_capture_on_commit_callbacks):
    en_attente = make_reservation(annonce, guest=make_user(email='ama@example.tg', first_name='Ama'), status='pending')
    make_reservation(annonce, starts_in=-10)

    with django_capture_on_commit_callbacks(execute=True):
        assert _supprimer(client_for, annonce).status_code == 204

    en_attente.refresh_from_db()
    assert (en_attente.status, en_attente.annule_par) == ('cancelled', 'hote')
    assert en_attente.annule_le is not None
    assert [m.to for m in mailoutbox] == [['ama@example.tg']]
    assert 'Bonjour Ama' in mailoutbox[0].body and annonce.name in mailoutbox[0].body


def test_no_email_when_the_archiving_is_refused(client_for, annonce, make_reservation, mailoutbox,
                                                django_capture_on_commit_callbacks):
    make_reservation(annonce, status='pending')
    make_reservation(annonce)

    with django_capture_on_commit_callbacks(execute=True):
        assert _supprimer(client_for, annonce).status_code == 409

    assert mailoutbox == []
    assert ReservationModel.objects.filter(hebergement_id=annonce.id, status='pending').exists()


@pytest.mark.parametrize('starts_in, nights', [(10, 3), (-1, 3), (-3, 3)])
def test_refused_while_a_paid_stay_is_upcoming_or_in_progress(client_for, annonce, make_reservation, starts_in, nights):
    make_reservation(annonce, starts_in=starts_in, nights=nights)

    reponse = _supprimer(client_for, annonce)

    assert reponse.status_code == 409 and 'Masquez-la' in reponse.data['detail']
    assert HebergementModel.objects.filter(pk=annonce.pk, archivee_le__isnull=True).exists()


def test_archived_listing_disappears_from_the_site_and_the_host_space(client_for, make_user, annonce):
    _supprimer(client_for, annonce)
    voyageur = client_for(make_user())

    assert not HebergementModel.objects.publiees().filter(pk=annonce.pk).exists()
    assert voyageur.get(f'{HEBERGEMENTS}{annonce.id}/').status_code == 404
    assert client_for(annonce.host).get(f'{HEBERGEMENTS}mine/').data['results'] == []
    assert _supprimer(client_for, annonce).status_code == 404


def test_archived_listing_cannot_be_booked(client_for, make_user, annonce):
    _supprimer(client_for, annonce)
    debut = timezone.localdate() + timedelta(days=10)

    reponse = client_for(make_user()).post('/api/v1/reservations/', {
        'hebergement': str(annonce.id), 'check_in': debut.isoformat(),
        'check_out': (debut + timedelta(days=2)).isoformat(),
    }, format='json')

    assert reponse.status_code == 400


def test_conversations_about_an_archived_listing_stay_readable(client_for, make_user, annonce):
    voyageur = make_user()
    maintenant = timezone.now()
    ConversationModel.objects.create(hebergement_id=annonce.id, guest=voyageur, host=annonce.host,
                                     created_at=maintenant, last_message_at=maintenant)
    _supprimer(client_for, annonce)

    reponse = client_for(voyageur).get('/api/v1/messaging/conversations/')

    assert reponse.data['results'][0]['hebergement']['name'] == annonce.name


def test_back_office_deletion_archives_too(client_for, make_user, annonce, make_reservation):
    make_reservation(annonce, starts_in=-10, nights=3)

    admin = client_for(make_user(role='admin'))

    assert admin.delete(f'{ADMIN}{annonce.id}/?motif=Annonce frauduleuse').status_code == 204

    assert HebergementModel.tous.get(pk=annonce.pk).archivee_le is not None
    assert ReservationModel.objects.filter(hebergement_id=annonce.id).count() == 1


class TestRestauration:
    @pytest.fixture
    def admin(self, client_for, make_user):
        return client_for(make_user(role='admin'))

    def test_archived_listings_are_listed_on_request_only(self, client_for, admin, annonce, make_hebergement):
        make_hebergement(name='Active')
        _supprimer(client_for, annonce)

        assert [h['name'] for h in admin.get(ADMIN).data['results']] == ['Active']
        archivees = admin.get(ADMIN, {'archivees': 'true'}).data['results']
        assert [h['id'] for h in archivees] == [str(annonce.id)] and archivees[0]['archivee_le']

    def test_restoring_brings_the_listing_back_hidden(self, client_for, admin, annonce):
        _supprimer(client_for, annonce)

        reponse = admin.post(f'{ADMIN}{annonce.id}/restaurer/')

        assert reponse.status_code == 200 and reponse.data['archivee_le'] is None
        restauree = HebergementModel.objects.get(pk=annonce.pk)
        assert not restauree.is_available
        assert [h['id'] for h in client_for(annonce.host).get(f'{HEBERGEMENTS}mine/').data['results']] == [str(annonce.id)]
        assert JournalAuditModel.objects.filter(action='annonce_restauree').exists()

    def test_only_an_archived_listing_can_be_restored(self, admin, annonce):
        assert admin.post(f'{ADMIN}{annonce.id}/restaurer/').status_code == 404

    def test_reserved_to_administrators(self, client_for, annonce):
        _supprimer(client_for, annonce)
        assert client_for(annonce.host).post(f'{ADMIN}{annonce.id}/restaurer/').status_code == 403
