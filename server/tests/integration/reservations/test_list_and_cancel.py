RESERVATIONS = '/api/v1/reservations/'


def _ids(response):
    return {r['id'] for r in response.data['results']}


def test_guest_sees_only_own_reservations(client_for, make_user, make_hebergement, make_reservation):
    guest = make_user()
    mine = make_reservation(make_hebergement(), guest=guest)
    make_reservation(make_hebergement())

    assert _ids(client_for(guest).get(RESERVATIONS)) == {str(mine.id)}


def test_host_sees_reservations_of_own_listings(client_for, make_user, make_hebergement, make_reservation):
    host = make_user(role='hote')
    received = make_reservation(make_hebergement(host=host))
    make_reservation(make_hebergement())

    assert _ids(client_for(host).get(RESERVATIONS, {'as': 'host'})) == {str(received.id)}


def test_detail_visible_to_its_guest_only(client_for, make_user, make_hebergement, make_reservation):
    host = make_user(role='hote')
    reservation = make_reservation(make_hebergement(host=host))
    url = f'{RESERVATIONS}{reservation.id}/'

    assert client_for(reservation.guest).get(url).status_code == 200
    assert client_for(host).get(url).status_code == 404
    assert client_for(make_user()).get(url).status_code == 404


def test_cancel_before_check_in_frees_the_dates(client_for, make_user, make_hebergement, make_reservation):
    hebergement = make_hebergement()
    reservation = make_reservation(hebergement)

    assert client_for(reservation.guest).delete(f'{RESERVATIONS}{reservation.id}/').status_code in (200, 204)
    reservation.refresh_from_db()
    assert reservation.status == 'cancelled'

    response = client_for(make_user()).post(RESERVATIONS, {
        'hebergement': str(hebergement.id),
        'check_in': reservation.check_in.isoformat(),
        'check_out': reservation.check_out.isoformat(),
    }, format='json')
    assert response.status_code == 201


def test_started_stay_cannot_be_cancelled(client_for, make_hebergement, make_reservation):
    reservation = make_reservation(make_hebergement(), starts_in=0)
    assert client_for(reservation.guest).delete(f'{RESERVATIONS}{reservation.id}/').status_code == 400


def test_other_user_cannot_cancel(client_for, make_user, make_hebergement, make_reservation):
    reservation = make_reservation(make_hebergement())
    assert client_for(make_user()).delete(f'{RESERVATIONS}{reservation.id}/').status_code == 404
    reservation.refresh_from_db()
    assert reservation.status == 'confirmed'


def test_can_review_flag(client_for, make_hebergement, make_reservation):
    finished = make_reservation(make_hebergement(), starts_in=-5, nights=3)
    response = client_for(finished.guest).get(RESERVATIONS)
    [row] = response.data['results']
    assert row['peut_evaluer'] is True
    assert row['avis_id'] is None


def test_landmark_only_once_the_booking_is_paid(client_for, make_hebergement, make_reservation):
    hebergement = make_hebergement(point_repere='Derrière la pharmacie de Bè Kpota')
    payee = make_reservation(hebergement)
    en_attente = make_reservation(hebergement, starts_in=30, status='pending')
    client = client_for(payee.guest)

    assert client.get(f'{RESERVATIONS}{payee.id}/').data['point_repere'] == 'Derrière la pharmacie de Bè Kpota'
    assert client_for(en_attente.guest).get(f'{RESERVATIONS}{en_attente.id}/').data['point_repere'] is None
