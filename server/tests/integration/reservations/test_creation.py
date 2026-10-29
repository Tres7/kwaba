from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.reservations.models import ReservationModel

RESERVATIONS = '/api/v1/reservations/'


def _stay_dates(starts_in=10, nights=3):
    check_in = timezone.localdate() + timedelta(days=starts_in)
    return check_in, check_in + timedelta(days=nights)


def _book(client, hebergement, check_in, check_out, **extra):
    payload = {
        'hebergement': str(hebergement.id),
        'check_in': check_in.isoformat(),
        'check_out': check_out.isoformat(),
        'guests_count': 2,
        **extra,
    }
    return client.post(RESERVATIONS, payload, format='json')


def test_total_price_includes_service_fee(client_for, make_user, make_hebergement, settings):
    # Online payment disabled (whatever the keys of a local server/.env): direct confirmation
    settings.FEDAPAY = {**settings.FEDAPAY, 'SECRET_KEY': ''}
    settings.PAYPAL = {**settings.PAYPAL, 'CLIENT_ID': '', 'CLIENT_SECRET': ''}
    hebergement = make_hebergement(price_per_night=25000)
    check_in, check_out = _stay_dates(nights=3)

    response = _book(client_for(make_user()), hebergement, check_in, check_out,
                     status='cancelled', total_price=1)

    assert response.status_code == 201
    # 3 nights x 25,000 + 6 %; the status and price sent by the client are ignored
    assert Decimal(str(response.data['total_price'])) == Decimal('79500')
    assert response.data['status'] == 'confirmed'


def test_overlap_rejected_but_check_in_on_previous_check_out_accepted(client_for, make_user, make_hebergement):
    hebergement = make_hebergement()
    check_in, check_out = _stay_dates(nights=3)
    assert _book(client_for(make_user()), hebergement, check_in, check_out).status_code == 201

    other_guest = client_for(make_user())
    overlapping = _book(other_guest, hebergement, check_in + timedelta(days=1), check_out + timedelta(days=1))
    assert overlapping.status_code == 400
    assert 'check_in' in overlapping.data

    assert _book(other_guest, hebergement, check_out, check_out + timedelta(days=2)).status_code == 201


def test_cancelled_reservation_does_not_block_dates(client_for, make_user, make_hebergement):
    hebergement = make_hebergement()
    check_in, check_out = _stay_dates()
    ReservationModel.objects.create(hebergement_id=hebergement.id, guest_id=make_user().pk, check_in=check_in,
                                    check_out=check_out, total_price=0, status='cancelled')

    assert _book(client_for(make_user()), hebergement, check_in, check_out).status_code == 201


def test_host_cannot_book_own_hebergement(client_for, make_user, make_hebergement):
    host = make_user(role='hote')
    check_in, check_out = _stay_dates()
    response = _book(client_for(host), make_hebergement(host=host), check_in, check_out)
    assert response.status_code == 400
    assert 'hebergement' in response.data


def test_anonymous_user_rejected(api_client, make_hebergement):
    check_in, check_out = _stay_dates()
    assert _book(api_client, make_hebergement(), check_in, check_out).status_code == 401
