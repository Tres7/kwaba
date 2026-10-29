"""The host manages the unit types of their establishment: room types, stock, prices, closures per type."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.hebergements import stock
from apps.hebergements.models import BlocageModel, HebergementModel, TypeLogementModel
from apps.reservations.models import ReservationModel

HEBERGEMENTS = '/api/v1/hebergements/'


def _jour(n):
    return timezone.localdate() + timedelta(days=n)


@pytest.fixture
def hotel(make_hebergement):
    return make_hebergement(type='hotel', price_per_night=30000, max_guests=2)


def _types_url(h):
    return f'{HEBERGEMENTS}{h.id}/types/'


def _type_url(t):
    return f'{HEBERGEMENTS}types/{t.id}/'


def _suite(**extra):
    return {'nom': 'Suite', 'capacite': 4, 'prix_nuit': 80000, 'quantite': 2, **extra}


class TestManageTypes:
    def test_host_adds_a_room_type_and_the_listing_shows_from_price_and_max_capacity(self, client_for, hotel):
        client = client_for(hotel.host)
        hotel.types.update(prix_nuit=30000, quantite=5)
        assert client.post(_types_url(hotel), _suite(prix_nuit=25000), format='json').status_code == 201
        hotel.refresh_from_db()
        assert (hotel.price_per_night, hotel.max_guests) == (Decimal('25000'), 4)
        # Same display order, then the cheapest first
        assert [t['nom'] for t in client.get(_types_url(hotel)).data['results']] == ['Suite', 'Chambre']

    def test_others_cannot_see_or_change_them(self, client_for, make_user, hotel):
        autre = client_for(make_user(role='hote'))
        assert autre.get(_types_url(hotel)).status_code == 404
        assert autre.post(_types_url(hotel), _suite(), format='json').status_code == 404
        assert autre.patch(_type_url(hotel.types.get()), {'quantite': 9}, format='json').status_code == 404

    @pytest.mark.parametrize('champ, valeur', [('quantite', 0), ('quantite', 501), ('capacite', 0), ('prix_nuit', 0),
                                               ('photos', ['https://exemple-inconnu.test/a.jpg'])])
    def test_invalid_values(self, client_for, hotel, champ, valeur):
        assert client_for(hotel.host).post(_types_url(hotel), _suite(**{champ: valeur}), format='json').status_code == 400

    def test_contact_details_refused_in_the_name(self, client_for, hotel):
        reponse = client_for(hotel.host).post(_types_url(hotel), _suite(nom='Suite 90 12 34 56 WhatsApp'), format='json')
        assert reponse.status_code == 400 and 'nom' in reponse.data


class TestStockChanges:
    def test_quantity_never_below_the_units_already_booked(self, client_for, make_user, hotel):
        chambre = hotel.types.get()
        chambre.quantite = 5
        chambre.save()
        ReservationModel.objects.create(hebergement_id=hotel.id, type_logement_id=chambre.id, nb_unites=3, guest_id=make_user().pk,
                                        check_in=_jour(10), check_out=_jour(12), total_price=0, status='confirmed')
        client = client_for(hotel.host)
        refus = client.patch(_type_url(chambre), {'quantite': 2}, format='json')
        assert refus.status_code == 409 and '3 logements' in str(refus.data['quantite'])
        assert client.patch(_type_url(chambre), {'quantite': 3}, format='json').status_code == 200
        assert client.patch(_type_url(chambre), {'quantite': 8}, format='json').status_code == 200
        assert stock.restantes(TypeLogementModel.objects.get(pk=chambre.pk), _jour(10), _jour(12)) == 5

    def test_an_establishment_keeps_an_active_type(self, client_for, hotel):
        client = client_for(hotel.host)
        seul = hotel.types.get()
        assert client.patch(_type_url(seul), {'actif': False}, format='json').status_code == 400
        assert client.delete(_type_url(seul)).status_code == 400

    def test_a_booked_type_is_deactivated_not_deleted(self, client_for, make_user, hotel):
        client = client_for(hotel.host)
        client.post(_types_url(hotel), _suite(), format='json')
        suite = hotel.types.get(nom='Suite')
        ReservationModel.objects.create(hebergement_id=hotel.id, type_logement_id=suite.id, guest_id=make_user().pk, check_in=_jour(10),
                                        check_out=_jour(12), total_price=0, status='cancelled')
        assert client.delete(_type_url(suite)).status_code == 409
        assert client.patch(_type_url(suite), {'actif': False}, format='json').status_code == 200
        hotel.refresh_from_db()
        assert (hotel.price_per_night, hotel.max_guests) == (Decimal('30000'), 2)

    def test_an_unused_type_is_deleted(self, client_for, hotel):
        client = client_for(hotel.host)
        client.post(_types_url(hotel), _suite(), format='json')
        assert client.delete(_type_url(hotel.types.get(nom='Suite'))).status_code == 204
        assert list(hotel.types.values_list('nom', flat=True)) == ['Chambre']


class TestClosuresPerType:
    def url(self, h):
        return f'{HEBERGEMENTS}{h.id}/blocages/'

    def test_closing_one_type_only(self, client_for, hotel):
        client = client_for(hotel.host)
        client.post(_types_url(hotel), _suite(), format='json')
        suite, chambre = hotel.types.get(nom='Suite'), hotel.types.get(nom='Chambre')
        dates = {'debut': _jour(10).isoformat(), 'fin': _jour(12).isoformat()}
        reponse = client.post(self.url(hotel), {**dates, 'type_logement': str(suite.id)}, format='json')
        assert reponse.status_code == 201 and reponse.data['type_logement_nom'] == 'Suite'
        assert stock.restantes(suite, _jour(10), _jour(12)) == 0
        assert stock.restantes(chambre, _jour(10), _jour(12)) == 1
        # Another type can be closed over the same dates; the same type, or the whole establishment, cannot
        assert client.post(self.url(hotel), {**dates, 'type_logement': str(chambre.id)}, format='json').status_code == 201
        assert client.post(self.url(hotel), {**dates, 'type_logement': str(suite.id)}, format='json').status_code == 409
        assert client.post(self.url(hotel), dates, format='json').status_code == 409

    def test_bookings_of_another_type_do_not_prevent_the_closure(self, client_for, make_user, hotel):
        client = client_for(hotel.host)
        client.post(_types_url(hotel), _suite(), format='json')
        suite, chambre = hotel.types.get(nom='Suite'), hotel.types.get(nom='Chambre')
        ReservationModel.objects.create(hebergement_id=hotel.id, type_logement_id=chambre.id, guest_id=make_user().pk, check_in=_jour(10),
                                        check_out=_jour(12), total_price=0, status='confirmed')
        dates = {'debut': _jour(10).isoformat(), 'fin': _jour(12).isoformat()}
        assert client.post(self.url(hotel), {**dates, 'type_logement': str(chambre.id)}, format='json').status_code == 409
        assert client.post(self.url(hotel), {**dates, 'type_logement': str(suite.id)}, format='json').status_code == 201

    def test_type_of_another_establishment(self, client_for, hotel, make_hebergement):
        autre = make_hebergement().types.get()
        reponse = client_for(hotel.host).post(self.url(hotel), {'debut': _jour(10).isoformat(), 'fin': _jour(12).isoformat(),
                                                                'type_logement': str(autre.id)}, format='json')
        assert reponse.status_code == 400
        assert not BlocageModel.objects.exists()


def test_editing_the_listing_with_several_types_keeps_the_from_price(client_for, hotel):
    client = client_for(hotel.host)
    client.post(_types_url(hotel), _suite(prix_nuit=60000), format='json')
    client.patch(f'{HEBERGEMENTS}{hotel.id}/', {'price_per_night': 99000}, format='json')
    hotel = HebergementModel.objects.get(pk=hotel.pk)
    assert hotel.price_per_night == Decimal('30000')
    assert sorted(hotel.types.values_list('prix_nuit', flat=True)) == [Decimal('30000'), Decimal('60000')]


def test_host_calendar_of_one_type(client_for, make_user, hotel):
    client = client_for(hotel.host)
    client.post(_types_url(hotel), _suite(), format='json')
    suite, chambre = hotel.types.get(nom='Suite'), hotel.types.get(nom='Chambre')
    ReservationModel.objects.create(hebergement_id=hotel.id, type_logement_id=chambre.id, guest_id=make_user().pk, check_in=_jour(10),
                                    check_out=_jour(12), total_price=0, status='confirmed')
    BlocageModel.objects.create(hebergement=hotel, type_logement=suite, debut=_jour(20), fin=_jour(22))
    BlocageModel.objects.create(hebergement=hotel, debut=_jour(30), fin=_jour(31))
    url = f'{HEBERGEMENTS}{hotel.id}/disponibilites/'

    def periodes(**params):
        return [(p['type'], p['type_logement']) for p in client.get(url, params).data['periodes']]

    assert periodes() == [('reservation', 'Chambre'), ('blocage', 'Suite'), ('blocage', None)]
    assert periodes(type_logement=suite.id) == [('blocage', 'Suite'), ('blocage', None)]
    assert periodes(type_logement=chambre.id) == [('reservation', 'Chambre'), ('blocage', None)]
