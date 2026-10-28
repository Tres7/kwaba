"""Stock of the unit types, night by night: date boundaries, units, closures, expired payments, calendars."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.hebergements import stock
from apps.hebergements.disponibilites import conflit, est_disponible
from apps.hebergements.models import BlocageModel, TypeLogementModel
from apps.reservations.models import ReservationModel

HEBERGEMENTS = '/api/v1/hebergements/'


def _jour(n):
    return timezone.localdate() + timedelta(days=n)


@pytest.fixture
def hotel(make_hebergement):
    """A hotel: 3 standard doubles (its default type) and 1 suite."""
    h = make_hebergement(type='hotel', price_per_night=30000)
    h.types.update(nom='Double standard', quantite=3)
    TypeLogementModel.objects.create(hebergement=h, nom='Suite', capacite=4, prix_nuit=80000, quantite=1, ordre=1)
    return h


def _double(h):
    return h.types.get(nom='Double standard')


def _suite(h):
    return h.types.get(nom='Suite')


def _reserver(make_user, type_logement, debut, fin, nb=1, **extra):
    extra.setdefault('status', 'confirmed')
    return ReservationModel.objects.create(hebergement=type_logement.hebergement, type_logement=type_logement, nb_unites=nb,
                                           guest=make_user(), check_in=_jour(debut), check_out=_jour(fin), total_price=0, **extra)


class TestDateBoundaries:
    """Single unit: [check_in, check_out), the departure day is free for the next arrival."""

    @pytest.fixture
    def maison(self, make_hebergement):
        return make_hebergement(type='maison')

    def test_arrival_on_another_guest_departure_day(self, make_user, maison):
        unite = maison.types.get()
        _reserver(make_user, unite, 10, 13)
        assert stock.est_disponible(unite, _jour(13), _jour(15))
        assert stock.est_disponible(unite, _jour(8), _jour(10))  # leaves the day the other one arrives

    @pytest.mark.parametrize('debut, fin', [(12, 14), (9, 11), (10, 13), (11, 12), (8, 16)])
    def test_any_shared_night_conflicts(self, make_user, maison, debut, fin):
        unite = maison.types.get()
        _reserver(make_user, unite, 10, 13)
        assert not stock.est_disponible(unite, _jour(debut), _jour(fin))
        assert conflit(maison.id, _jour(debut), _jour(fin)) == "Ces dates sont déjà réservées pour cet hébergement."

    def test_one_night_stay(self, make_user, maison):
        unite = maison.types.get()
        _reserver(make_user, unite, 10, 11)
        assert stock.nuits(_jour(10), _jour(11)) == [_jour(10)]
        assert not stock.est_disponible(unite, _jour(10), _jour(11))
        assert stock.est_disponible(unite, _jour(11), _jour(12))

    def test_empty_period_is_never_available(self, maison):
        assert stock.restantes(maison.types.get(), _jour(5), _jour(5)) == 0


class TestUnits:
    def test_units_left_is_the_minimum_over_the_nights(self, make_user, hotel):
        double = _double(hotel)
        _reserver(make_user, double, 10, 12)            # nights 10, 11
        _reserver(make_user, double, 11, 14, nb=1)      # nights 11, 12, 13
        occupation = stock.Occupation([double], _jour(10), _jour(14))
        assert [occupation.restantes_nuit(double.id, _jour(n)) for n in range(10, 14)] == [2, 1, 2, 2]
        assert occupation.restantes(double.id) == 1
        assert stock.est_disponible(double, _jour(10), _jour(14), nb=1)
        assert not stock.est_disponible(double, _jour(10), _jour(14), nb=2)
        assert conflit(hotel.id, _jour(10), _jour(14), type_logement=double, nb=2) == (
            "Il ne reste que 1 logement de ce type disponible à ces dates.")

    def test_a_booking_of_several_units(self, make_user, hotel):
        double = _double(hotel)
        _reserver(make_user, double, 10, 12, nb=3)
        assert stock.restantes(double, _jour(10), _jour(12)) == 0
        assert stock.est_disponible(_suite(hotel), _jour(10), _jour(12))  # the other type is untouched

    @pytest.mark.parametrize('statut, expire, compte', [
        ('confirmed', None, True),
        ('pending', timedelta(minutes=10), True),     # payment in progress: dates held
        ('pending', timedelta(minutes=-1), False),    # payment expired: dates free again
        ('cancelled', None, False),
    ])
    def test_which_bookings_hold_units(self, make_user, hotel, statut, expire, compte):
        double = _double(hotel)
        _reserver(make_user, double, 10, 12, nb=3, status=statut, expire_le=timezone.now() + expire if expire else None)
        assert stock.restantes(double, _jour(10), _jour(12)) == (0 if compte else 3)

    def test_a_booking_without_type_counts_against_every_type(self, make_user, hotel):
        ReservationModel.objects.create(hebergement=hotel, guest=make_user(), check_in=_jour(10), check_out=_jour(12),
                                        total_price=0, status='confirmed')
        assert stock.restantes(_double(hotel), _jour(10), _jour(12)) == 2
        assert stock.restantes(_suite(hotel), _jour(10), _jour(12)) == 0

    def test_the_booking_being_confirmed_is_ignored(self, make_user, hotel):
        suite = _suite(hotel)
        r = _reserver(make_user, suite, 10, 12)
        assert conflit(hotel.id, _jour(10), _jour(12), type_logement=suite) is not None
        assert conflit(hotel.id, _jour(10), _jour(12), type_logement=suite, exclure=r.pk) is None


class TestClosures:
    def test_closing_the_establishment_closes_every_type(self, hotel):
        BlocageModel.objects.create(hebergement=hotel, debut=_jour(10), fin=_jour(11))
        for t in (_double(hotel), _suite(hotel)):
            assert stock.restantes(t, _jour(9), _jour(12)) == 0
            assert stock.est_disponible(t, _jour(11), _jour(12))
        assert conflit(hotel.id, _jour(10), _jour(11)) == "L'hôte a fermé ces dates à la réservation."

    def test_closing_one_type_leaves_the_others(self, hotel):
        BlocageModel.objects.create(hebergement=hotel, type_logement=_suite(hotel), debut=_jour(10), fin=_jour(12))
        assert stock.restantes(_suite(hotel), _jour(10), _jour(12)) == 0
        assert stock.restantes(_double(hotel), _jour(10), _jour(12)) == 3


def test_next_available_arrival(make_user, hotel):
    suite = _suite(hotel)
    _reserver(make_user, suite, 10, 14)
    assert stock.prochaine_date(suite, _jour(10), duree=2) == _jour(14)
    assert stock.prochaine_date(suite, _jour(5), duree=3) == _jour(5)        # 5, 6, 7: free
    assert stock.prochaine_date(suite, _jour(8), duree=3) == _jour(14)       # 8-10 would cross night 10
    _reserver(make_user, suite, 14, 90)
    assert stock.prochaine_date(suite, _jour(10), duree=2, horizon=30) is None


def test_establishment_is_available_while_one_type_has_a_unit(make_user, hotel):
    _reserver(make_user, _double(hotel), 10, 12, nb=3)
    assert est_disponible(hotel.id, _jour(10), _jour(12))
    _reserver(make_user, _suite(hotel), 10, 12)
    assert not est_disponible(hotel.id, _jour(10), _jour(12))


class TestPublicCalendar:
    def url(self, h):
        return f'{HEBERGEMENTS}{h.id}/disponibilites/'

    def test_a_night_is_grey_only_when_every_type_is_full(self, api_client, make_user, hotel):
        _reserver(make_user, _double(hotel), 10, 13, nb=3)
        _reserver(make_user, _suite(hotel), 11, 12)
        assert api_client.get(self.url(hotel)).data['periodes'] == [{'debut': _jour(11), 'fin': _jour(12)}]

    def test_calendar_of_one_type(self, api_client, make_user, hotel):
        _reserver(make_user, _double(hotel), 10, 13, nb=3)
        periodes = api_client.get(self.url(hotel), {'type_logement': str(_double(hotel).id)}).data['periodes']
        assert periodes == [{'debut': _jour(10), 'fin': _jour(13)}]

    @pytest.mark.parametrize('valeur', ['pas-un-uuid', '00000000-0000-0000-0000-000000000000'])
    def test_unknown_type(self, api_client, hotel, valeur):
        assert api_client.get(self.url(hotel), {'type_logement': valeur}).status_code == 400

    def test_host_sees_units_and_types(self, client_for, make_user, hotel):
        _reserver(make_user, _double(hotel), 10, 12, nb=2)
        (periode,) = client_for(hotel.host).get(self.url(hotel)).data['periodes']
        assert (periode['nb_unites'], periode['type_logement']) == (2, 'Double standard')
