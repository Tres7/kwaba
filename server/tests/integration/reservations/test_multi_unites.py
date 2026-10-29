"""Booking units of a unit type: chosen type, several units, stock left, capacity, price, payment confirmation."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.hebergements.models import TypeLogementModel
from apps.reservations.models import ReservationModel

RESERVATIONS = '/api/v1/reservations/'


@pytest.fixture(autouse=True)
def _paiement_hors_ligne(settings):
    settings.PAIEMENT_HORS_LIGNE = True


@pytest.fixture
def hotel(make_hebergement):
    h = make_hebergement(type='hotel', price_per_night=30000, max_guests=2)
    h.types.update(nom='Double standard', quantite=3)
    return h


def _sejour(nuits=2):
    arrivee = timezone.localdate() + timedelta(days=12)
    return arrivee, arrivee + timedelta(days=nuits)


def _reserver(client, hotel, **extra):
    arrivee, depart = _sejour()
    return client.post(RESERVATIONS, {'hebergement': str(hotel.id), 'check_in': arrivee.isoformat(),
                                      'check_out': depart.isoformat(), 'guests_count': 2, **extra}, format='json')


def test_booking_two_rooms_prices_both(client_for, make_user, hotel):
    reponse = _reserver(client_for(make_user()), hotel, nb_unites=2, guests_count=4)
    assert reponse.status_code == 201, reponse.data
    r = ReservationModel.objects.get(pk=reponse.data['id'])
    assert (TypeLogementModel.objects.get(pk=r.type_logement_id).nom, r.nb_unites, r.prix_nuits) == ('Double standard', 2, 2 * 2 * 30000)
    assert (reponse.data['type_logement_nom'], reponse.data['nb_unites']) == ('Double standard', 2)


def test_choosing_another_room_type(client_for, make_user, hotel):
    suite = TypeLogementModel.objects.create(hebergement=hotel, nom='Suite', capacite=4, prix_nuit=Decimal(80000), quantite=1)
    reponse = _reserver(client_for(make_user()), hotel, type_logement=str(suite.id), guests_count=4)
    assert reponse.status_code == 201, reponse.data
    assert ReservationModel.objects.get(pk=reponse.data['id']).prix_nuits == 2 * 80000


def test_the_last_units(client_for, make_user, hotel):
    assert _reserver(client_for(make_user()), hotel, nb_unites=2, guests_count=4).status_code == 201
    trop = _reserver(client_for(make_user()), hotel, nb_unites=2, guests_count=4)
    assert trop.status_code == 400
    assert 'Il ne reste que 1 logement' in str(trop.data['check_in'])
    assert _reserver(client_for(make_user()), hotel).status_code == 201
    assert _reserver(client_for(make_user()), hotel).status_code == 400


class TestRefused:
    def test_more_units_than_the_type_has(self, client_for, make_user, hotel):
        reponse = _reserver(client_for(make_user()), hotel, nb_unites=4, guests_count=4)
        assert reponse.status_code == 400 and 'nb_unites' in reponse.data

    def test_a_type_of_another_establishment(self, client_for, make_user, hotel, make_hebergement):
        autre = make_hebergement().types.get()
        reponse = _reserver(client_for(make_user()), hotel, type_logement=str(autre.id))
        assert reponse.status_code == 400 and 'type_logement' in reponse.data

    def test_an_inactive_type(self, client_for, make_user, hotel):
        hotel.types.update(actif=False)
        TypeLogementModel.objects.create(hebergement=hotel, nom='Suite', capacite=2, prix_nuit=50000, quantite=1)
        ferme = hotel.types.get(nom='Double standard')
        reponse = _reserver(client_for(make_user()), hotel, type_logement=str(ferme.id))
        assert reponse.status_code == 400 and 'type_logement' in reponse.data

    @pytest.mark.parametrize('unites, voyageurs', [(1, 3), (2, 5)])
    def test_more_guests_than_the_units_hold(self, client_for, make_user, hotel, unites, voyageurs):
        reponse = _reserver(client_for(make_user()), hotel, nb_unites=unites, guests_count=voyageurs)
        assert reponse.status_code == 400 and 'guests_count' in reponse.data


def test_payment_after_expiry_refunded_when_the_units_are_gone(make_user, hotel, monkeypatch):
    """A booking whose payment arrives late is confirmed only if its units are still free (stock checked again)."""
    from apps.paiements import api as paiements_api, services
    from apps.paiements.models import PaiementModel

    double = hotel.types.get()
    arrivee, depart = _sejour()
    en_retard = ReservationModel.objects.create(
        hebergement_id=hotel.id, type_logement_id=double.id, nb_unites=2, guest=make_user(), check_in=arrivee, check_out=depart,
        total_price=0, status='cancelled', annule_par='expiration')
    ReservationModel.objects.create(hebergement_id=hotel.id, type_logement_id=double.id, nb_unites=2, guest=make_user(),
                                    check_in=arrivee, check_out=depart, total_price=0, status='confirmed')
    paiement = PaiementModel.objects.create(reservation_id=en_retard.id, montant=1000, statut='en_attente')
    rembourses = []
    monkeypatch.setattr(paiements_api, 'rembourser', lambda p, montant, motif: rembourses.append(motif))  # no real refund

    services._paiement_reussi(paiement.pk, {})

    en_retard.refresh_from_db()
    assert en_retard.status == 'cancelled' and rembourses == ["Dates plus disponibles au moment du paiement"]


@pytest.mark.parametrize('cas, motif', [
    ('paye_deux_fois', "Paiement reçu en double"),
    ('annulee_avant', "Réservation annulée avant la confirmation du paiement"),
])
def test_payment_refunded_when_paid_twice_or_cancelled_before(make_user, hotel, monkeypatch, cas, motif):
    from apps.paiements import api as paiements_api, services
    from apps.paiements.models import PaiementModel

    arrivee, depart = _sejour()
    reservation = ReservationModel.objects.create(
        hebergement_id=hotel.id, type_logement_id=hotel.types.get().id, guest=make_user(), check_in=arrivee,
        check_out=depart, total_price=1000, status='cancelled' if cas == 'annulee_avant' else 'confirmed',
        annule_par='voyageur' if cas == 'annulee_avant' else '')
    if cas == 'paye_deux_fois':
        PaiementModel.objects.create(reservation_id=reservation.id, montant=1000, statut='reussi', transaction_id='T-1')
    paiement = PaiementModel.objects.create(reservation_id=reservation.id, montant=1000, statut='en_attente',
                                            transaction_id='T-2')
    rembourses = []
    monkeypatch.setattr(paiements_api, 'rembourser', lambda p, montant, m: rembourses.append((montant, m)))

    services._paiement_reussi(paiement.pk, {})

    assert rembourses == [(1000, motif)]
