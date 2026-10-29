from datetime import timedelta

import pytest
from django.utils import timezone

from apps.hebergements.models import BlocageModel

HEBERGEMENTS = '/api/v1/hebergements/'


def _names(response):
    assert response.status_code == 200
    return {h['name'] for h in response.data['results']}


@pytest.fixture
def listings(make_user, make_hebergement):
    host = make_user(role='hote')
    return {
        'villa': make_hebergement(host=host, name='Villa Lomé', city='Lomé', type='villa',
                                  price_per_night=50000, max_guests=6, rating=4.8),
        'appart': make_hebergement(host=host, name='Appart Kpalimé', city='Kpalimé', location='Centre',
                                   type='appartement', price_per_night=15000, max_guests=2, rating=4.1),
        'hotel': make_hebergement(host=host, name='Hôtel du Golfe', city='Lomé', location='Bè',
                                  type='hotel', price_per_night=30000, max_guests=2, rating=3.5),
        'hidden': make_hebergement(host=host, name='Masqué', city='Lomé', is_available=False),
    }


def test_only_available_listings(api_client, listings):
    assert _names(api_client.get(HEBERGEMENTS)) == {'Villa Lomé', 'Appart Kpalimé', 'Hôtel du Golfe'}


@pytest.mark.parametrize('params, expected', [
    ({'city': 'lomé'}, {'Villa Lomé', 'Hôtel du Golfe'}),
    ({'city': 'Bè'}, {'Hôtel du Golfe'}),
    ({'type': 'appartement'}, {'Appart Kpalimé'}),
    ({'price_min': 20000, 'price_max': 40000}, {'Hôtel du Golfe'}),
    ({'guests': 4}, {'Villa Lomé'}),
    ({'q': 'golfe'}, {'Hôtel du Golfe'}),
    ({'city': 'Lomé', 'guests': 3}, {'Villa Lomé'}),
])
def test_filters(api_client, listings, params, expected):
    assert _names(api_client.get(HEBERGEMENTS, params)) == expected


@pytest.mark.parametrize('sort, expected', [
    ('prix_asc', ['Appart Kpalimé', 'Hôtel du Golfe', 'Villa Lomé']),
    ('prix_desc', ['Villa Lomé', 'Hôtel du Golfe', 'Appart Kpalimé']),
    ('note', ['Villa Lomé', 'Appart Kpalimé', 'Hôtel du Golfe']),
])
def test_sorting(api_client, listings, sort, expected):
    response = api_client.get(HEBERGEMENTS, {'sort': sort})
    assert [h['name'] for h in response.data['results']] == expected


def test_limit(api_client, listings):
    assert len(api_client.get(HEBERGEMENTS, {'limit': 2}).data['results']) == 2


def _dates(check_in, nuits=2):
    return {'check_in': check_in.isoformat(), 'check_out': (check_in + timedelta(days=nuits)).isoformat()}


def test_full_listings_stay_after_the_available_ones(api_client, listings, make_reservation):
    check_in = timezone.localdate() + timedelta(days=10)
    make_reservation(listings['villa'], starts_in=10, nights=3)
    BlocageModel.objects.create(hebergement=listings['appart'], debut=check_in, fin=check_in + timedelta(days=1))
    make_reservation(listings['hotel'], starts_in=10, nights=3, status='cancelled')

    resultats = api_client.get(HEBERGEMENTS, {**_dates(check_in), 'sort': 'prix_asc'}).data['results']
    assert [(h['name'], h['disponibilite']['disponible']) for h in resultats] == [
        ('Hôtel du Golfe', True), ('Appart Kpalimé', False), ('Villa Lomé', False)]
    # The full ones keep their photos and description, with the next arrival for the same stay
    appart = resultats[1]
    assert appart['image_url'] == listings['appart'].image_url
    assert appart['disponibilite']['prochaine_date'] == check_in + timedelta(days=1)
    assert resultats[2]['disponibilite']['prochaine_date'] == check_in + timedelta(days=3)


def test_available_only(api_client, listings, make_reservation):
    make_reservation(listings['villa'], starts_in=10, nights=3)
    check_in = timezone.localdate() + timedelta(days=10)
    noms = _names(api_client.get(HEBERGEMENTS, {**_dates(check_in), 'disponibles': 'true'}))
    assert noms == {'Hôtel du Golfe', 'Appart Kpalimé'}


def test_units_left_for_a_hotel(api_client, listings, make_user):
    from apps.reservations.models import ReservationModel
    hotel = listings['hotel']
    hotel.types.update(quantite=5)
    check_in = timezone.localdate() + timedelta(days=10)
    ReservationModel.objects.create(hebergement_id=hotel.id, type_logement_id=hotel.types.get().id, nb_unites=3, guest=make_user(),
                                    check_in=check_in, check_out=check_in + timedelta(days=2), total_price=0,
                                    status='confirmed')
    (ligne,) = [h for h in api_client.get(HEBERGEMENTS, _dates(check_in)).data['results'] if h['name'] == 'Hôtel du Golfe']
    assert ligne['disponibilite'] == {'disponible': True, 'unites_restantes': 2, 'unites_total': 5, 'prochaine_date': None}


def test_without_dates_no_availability_is_computed(api_client, listings):
    assert {h['disponibilite'] for h in api_client.get(HEBERGEMENTS).data['results']} == {None}


@pytest.mark.parametrize('nuits', [0, -2])
def test_departure_not_after_arrival_ignores_the_dates(api_client, listings, nuits):
    check_in = timezone.localdate() + timedelta(days=10)
    reponse = api_client.get(HEBERGEMENTS, _dates(check_in, nuits))
    assert reponse.status_code == 200 and len(reponse.data['results']) == 3


def test_check_in_on_check_out_day_keeps_listing(api_client, listings, make_reservation):
    reservation = make_reservation(listings['villa'], starts_in=10, nights=3)
    params = {
        'check_in': reservation.check_out.isoformat(),
        'check_out': (reservation.check_out + timedelta(days=2)).isoformat(),
    }
    assert 'Villa Lomé' in _names(api_client.get(HEBERGEMENTS, params))


def test_is_favorite_for_current_user(client_for, make_user, listings):
    from apps.favoris.models import FavoriModel
    user = make_user()
    FavoriModel.objects.create(user=user, hebergement_id=listings['villa'].id)

    results = client_for(user).get(HEBERGEMENTS).data['results']
    assert {h['name']: h['is_favorite'] for h in results} == {
        'Villa Lomé': True, 'Appart Kpalimé': False, 'Hôtel du Golfe': False,
    }


def test_query_count_does_not_grow_with_results(api_client, make_hebergement, django_assert_max_num_queries):
    for i in range(15):
        make_hebergement(name=f'Logement {i}')
    with django_assert_max_num_queries(3):
        api_client.get(HEBERGEMENTS)


@pytest.mark.parametrize('params', [
    {'check_in': 'abc', 'check_out': 'def'},
    {'price_min': 'abc'},
    {'price_max': 'abc'},
])
def test_invalid_search_parameters_return_400_not_500(raw_client, listings, params):
    assert raw_client.get(HEBERGEMENTS, params).status_code == 400


def test_popular_cities(api_client, make_user, make_hebergement):
    host = make_user(role='hote')
    for city, count in [('Lomé', 3), ('Kara', 1), ('Aného', 1)]:
        for _ in range(count):
            make_hebergement(host=host, city=city)
    make_hebergement(host=host, city='Kara', is_available=False)
    make_hebergement(host=host, city='Lomé', rating=4.9, image_url='https://cdn.example/lome.jpg')

    rows = api_client.get(f'{HEBERGEMENTS}villes/').data['results']
    assert [(r['city'], r['count']) for r in rows] == [('Lomé', 4), ('Aného', 1), ('Kara', 1)]
    assert rows[0]['image_url'] == 'https://cdn.example/lome.jpg'


def test_empty_parameters_are_ignored(api_client, listings):
    params = {'price_min': '', 'price_max': '', 'check_in': '', 'check_out': ''}
    assert _names(api_client.get(HEBERGEMENTS, params)) == {'Villa Lomé', 'Appart Kpalimé', 'Hôtel du Golfe'}


def test_negative_price_rejected(api_client, listings):
    response = api_client.get(HEBERGEMENTS, {'price_min': -1})
    assert response.status_code == 400
    assert 'price_min' in response.data


def test_filtre_par_equipements_et_quartier(api_client, make_hebergement):
    piscine_wifi = make_hebergement(name='Villa piscine', location='Bè Kpota', amenities=['piscine', 'wifi', 'clim'])
    make_hebergement(name='Studio wifi', location='Tokoin', amenities=['wifi'])
    make_hebergement(name='Sans rien', location='Tokoin', amenities=[])

    def noms(params):
        return _names(api_client.get(HEBERGEMENTS, params))

    assert noms({'equipements': 'wifi'}) == {'Villa piscine', 'Studio wifi'}
    assert noms({'equipements': 'piscine,wifi'}) == {piscine_wifi.name}
    assert noms({'equipements': 'spa'}) == set()
    # A Lomé district chosen in the destination field also searches in the address
    assert noms({'city': 'Tokoin'}) == {'Studio wifi', 'Sans rien'}
