"""Safety rules around bookings: default status, pending bookings without a deadline, private calendars, list queries."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.hebergements.disponibilites import est_disponible
from apps.paiements import services as paiements
from apps.reservations.models import ReservationModel

HEBERGEMENTS = '/api/v1/hebergements/'
RESERVATIONS = '/api/v1/reservations/'


def test_a_booking_created_without_a_status_is_not_confirmed(make_user, make_hebergement):
    debut = timezone.localdate() + timedelta(days=5)
    reservation = ReservationModel.objects.create(hebergement_id=make_hebergement().id, guest=make_user(), check_in=debut,
                                                  check_out=debut + timedelta(days=2), total_price=0)
    assert reservation.status == 'pending'


class TestPendingWithoutDeadline:
    """Old pending bookings had no expire_le: they must not hold their dates forever."""

    def _pending(self, make_user, hebergement, cree_il_y_a: timedelta):
        debut = timezone.localdate() + timedelta(days=10)
        reservation = ReservationModel.objects.create(hebergement_id=hebergement.id, guest=make_user(), check_in=debut,
                                                      check_out=debut + timedelta(days=3), total_price=0,
                                                      status='pending', expire_le=None)
        ReservationModel.objects.filter(pk=reservation.pk).update(created_at=timezone.now() - cree_il_y_a)
        return reservation

    def test_recent_one_holds_its_dates(self, make_user, make_hebergement):
        hebergement = make_hebergement()
        r = self._pending(make_user, hebergement, timedelta(minutes=1))
        assert not est_disponible(hebergement.id, r.check_in, r.check_out)

    def test_old_one_frees_its_dates_and_expires(self, make_user, make_hebergement):
        hebergement = make_hebergement()
        r = self._pending(make_user, hebergement, paiements.delai_paiement() + timedelta(minutes=1))
        assert est_disponible(hebergement.id, r.check_in, r.check_out)

        assert paiements.expirer_reservations() == 1
        r.refresh_from_db()
        assert (r.status, r.annule_par) == ('cancelled', 'expiration')


class TestCalendarOfUnpublishedListing:
    def url(self, hebergement):
        return f'{HEBERGEMENTS}{hebergement.id}/disponibilites/'

    def test_hidden_from_visitors(self, api_client, client_for, make_user, make_hebergement):
        en_attente = make_hebergement(statut_verification='en_attente')
        assert api_client.get(self.url(en_attente)).status_code == 404
        assert client_for(make_user()).get(self.url(en_attente)).status_code == 404

    @pytest.mark.parametrize('role', ['agent', 'admin'])
    def test_visible_to_its_host_and_the_team(self, client_for, make_user, make_hebergement, role):
        en_attente = make_hebergement(statut_verification='en_attente')
        assert client_for(en_attente.host).get(self.url(en_attente)).status_code == 200
        assert client_for(make_user(role=role)).get(self.url(en_attente)).status_code == 200

    def test_published_listing_stays_public(self, api_client, make_hebergement):
        assert api_client.get(self.url(make_hebergement())).status_code == 200


def test_booking_list_query_count_does_not_grow(client_for, make_user, make_hebergement, make_reservation,
                                                django_assert_max_num_queries):
    voyageur = make_user()
    client = client_for(voyageur)
    make_reservation(make_hebergement(), guest=voyageur, starts_in=-10)
    with django_assert_max_num_queries(12) as une:
        client.get(RESERVATIONS)
    for i in range(5):
        make_reservation(make_hebergement(), guest=voyageur, starts_in=-20 - i * 5)
    with django_assert_max_num_queries(len(une.captured_queries)):
        assert client.get(RESERVATIONS).data['count'] == 6
