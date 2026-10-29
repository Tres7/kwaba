import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.hebergements.models import HebergementModel
from apps.paiements import services as paiements
from apps.reservations.models import ReservationModel

LANCEMENT = '/api/v1/hebergements/lancement/'
HEBERGEMENTS = '/api/v1/hebergements/'
RESERVATIONS = '/api/v1/reservations/'


def _book(client, hebergement):
    check_in = timezone.localdate() + timedelta(days=10)
    return client.post(RESERVATIONS, {
        'hebergement': str(hebergement.id), 'check_in': check_in.isoformat(),
        'check_out': (check_in + timedelta(days=3)).isoformat(), 'guests_count': 2,
    }, format='json')


@pytest.fixture
def prelancement(settings):
    settings.PRELANCEMENT = True


def test_status_endpoint_reports_the_mode(api_client, settings):
    assert api_client.get(LANCEMENT).data == {'prelancement': False}
    settings.PRELANCEMENT = True
    assert api_client.get(LANCEMENT).data == {'prelancement': True}


@pytest.mark.usefixtures('prelancement')
class TestPrelaunchOn:
    def test_verified_listing_is_hidden_from_the_public(self, api_client, make_hebergement):
        hebergement = make_hebergement(name='Villa Océane')

        assert api_client.get(HEBERGEMENTS).data['count'] == 0
        assert api_client.get(f'{HEBERGEMENTS}villes/').data['results'] == []
        assert api_client.get(f'{HEBERGEMENTS}{hebergement.id}/').status_code == 404

    def test_host_and_agents_still_see_the_listing(self, client_for, make_user, make_hebergement):
        hote = make_user(role='hote')
        hebergement = make_hebergement(host=hote)

        assert client_for(hote).get(f'{HEBERGEMENTS}mine/').data['count'] == 1
        assert client_for(hote).get(f'{HEBERGEMENTS}{hebergement.id}/').status_code == 200
        assert client_for(make_user(role='agent')).get(f'{HEBERGEMENTS}{hebergement.id}/').status_code == 200

    def test_booking_is_refused_by_the_api(self, client_for, make_user, make_hebergement):
        response = _book(client_for(make_user()), make_hebergement())

        assert response.status_code == 403
        assert response.data['code'] == 'prelancement'
        assert not ReservationModel.objects.exists()

    @pytest.mark.parametrize('path', [
        f'/api/v1/paiements/reservations/{uuid.uuid4()}/payer/',
        '/api/v1/transferts/',
        f'/api/v1/transferts/{uuid.uuid4()}/payer/',
        '/api/v1/locations/',
        f'/api/v1/locations/{uuid.uuid4()}/payer/',
        '/api/v1/give/dons/',
    ])
    def test_every_payment_entry_point_is_refused(self, client_for, make_user, path):
        response = client_for(make_user()).post(path, {}, format='json')

        assert response.status_code == 403
        assert response.data['code'] == 'prelancement'

    def test_no_payment_can_be_created_even_without_the_view_check(self, make_user, make_hebergement, make_reservation):
        reservation = make_reservation(make_hebergement(), status='pending')

        with pytest.raises(paiements.PaiementErreur):
            paiements.creer_paiement(type_objet='reservation', objet_id=reservation.id, montant=1000, moyen='mobile_money', description='test',
                                     url_retour='https://kwa-ba.com', voyageur=reservation.guest)


def test_prelaunch_off_keeps_the_usual_behaviour(api_client, client_for, make_user, make_hebergement, settings):
    settings.FEDAPAY = {**settings.FEDAPAY, 'SECRET_KEY': ''}
    settings.PAYPAL = {**settings.PAYPAL, 'CLIENT_ID': '', 'CLIENT_SECRET': ''}
    hebergement = make_hebergement()

    assert api_client.get(HEBERGEMENTS).data['count'] == 1
    assert api_client.get(f'{HEBERGEMENTS}{hebergement.id}/').status_code == 200
    assert _book(client_for(make_user()), hebergement).status_code == 201


def test_at_the_opening_the_oldest_listings_come_first(api_client, make_hebergement):
    premier = make_hebergement(name='Inscrit en premier')
    dernier = make_hebergement(name='Inscrit ensuite')
    HebergementModel.objects.filter(pk=premier.pk).update(created_at=dernier.created_at - timedelta(days=30))

    noms = [h['name'] for h in api_client.get(HEBERGEMENTS).data['results']]

    assert noms == ['Inscrit en premier', 'Inscrit ensuite']
    # Explicit sorts are unchanged
    assert api_client.get(HEBERGEMENTS, {'sort': 'prix_asc'}).status_code == 200
