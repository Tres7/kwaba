import pytest

from apps.hebergements.models import HebergementModel

HEBERGEMENTS = '/api/v1/hebergements/'


def _listing(**overrides):
    return {
        'name': 'Villa Océane',
        'city': 'Lomé',
        'type': 'villa',
        'price_per_night': 45000,
        'max_guests': 4,
        'surface_m2': 70, 'chambres': 2, 'lits_doubles': 1, 'lits_simples': 1, 'petit_dejeuner': 'non',
        **overrides,
    }


class TestCreate:
    def test_host_creates_listing(self, client_for, make_user):
        host = make_user(role='hote')
        response = client_for(host).post(HEBERGEMENTS, _listing(rating=5, review_count=99), format='json')

        assert response.status_code == 201
        listing = HebergementModel.objects.get(pk=response.data['id'])
        assert listing.host_id == host.id
        # The rating and the number of reviews never come from the client
        assert (listing.rating, listing.review_count) == (0.0, 0)

    def test_guest_forbidden(self, client_for, make_user):
        assert client_for(make_user()).post(HEBERGEMENTS, _listing(), format='json').status_code == 403

    def test_anonymous_unauthorized(self, api_client):
        assert api_client.post(HEBERGEMENTS, _listing(), format='json').status_code == 401

    @pytest.mark.parametrize('overrides, field', [
        ({'price_per_night': 0}, 'price_per_night'),
        ({'amenities': ['teleporteur']}, 'amenities'),
        ({'images': 'https://cdn.example/a.jpg'}, 'images'),
    ])
    def test_invalid_fields(self, client_for, make_user, overrides, field):
        response = client_for(make_user(role='hote')).post(HEBERGEMENTS, _listing(**overrides), format='json')
        assert response.status_code == 400
        assert field in response.data

    def test_images_truncated_to_ten(self, client_for, make_user):
        images = [f'https://images.unsplash.com/photo-{i}.jpg' for i in range(12)]
        response = client_for(make_user(role='hote')).post(HEBERGEMENTS, _listing(images=images), format='json')
        assert len(HebergementModel.objects.get(pk=response.data['id']).images) == 10

    @pytest.mark.parametrize('url', [
        'https://pixel-espion.example/a.jpg',     # host's server: would collect the visitors' IP address
        'http://images.unsplash.com/a.jpg',       # no HTTPS in production
        'javascript:alert(1)',
        'https://images.unsplash.com.attaquant.example/a.jpg',
    ])
    def test_images_from_unknown_hosts_rejected(self, client_for, make_user, url):
        client = client_for(make_user(role='hote'))
        assert client.post(HEBERGEMENTS, _listing(images=[url]), format='json').status_code == 400
        assert client.post(HEBERGEMENTS, _listing(image_url=url), format='json').status_code == 400

    def test_zero_guests_rejected(self, client_for, make_user):
        response = client_for(make_user(role='hote')).post(HEBERGEMENTS, _listing(max_guests=0), format='json')
        assert response.status_code == 400


class TestUpdateAndDelete:
    def test_unknown_listing(self, api_client):
        assert api_client.get(f'{HEBERGEMENTS}00000000-0000-0000-0000-000000000000/').status_code == 404

    def test_host_partial_update(self, client_for, make_hebergement):
        listing = make_hebergement()
        response = client_for(listing.host).patch(f'{HEBERGEMENTS}{listing.id}/', {'price_per_night': 30000},
                                                  format='json')
        assert response.status_code == 200
        listing.refresh_from_db()
        assert listing.price_per_night == 30000
        assert listing.name == 'Villa test'

    def test_other_user_cannot_update_or_delete(self, client_for, make_user, make_hebergement):
        listing = make_hebergement()
        intruder = client_for(make_user(role='hote'))
        assert intruder.patch(f'{HEBERGEMENTS}{listing.id}/', {'name': 'Pirate'}, format='json').status_code == 403
        assert intruder.delete(f'{HEBERGEMENTS}{listing.id}/').status_code == 403
        assert HebergementModel.objects.filter(pk=listing.id).exists()

    def test_host_deletes_listing_with_cascade(self, client_for, make_hebergement, make_reservation):
        listing = make_hebergement()
        reservation = make_reservation(listing)

        assert client_for(listing.host).delete(f'{HEBERGEMENTS}{listing.id}/').status_code == 204
        assert not HebergementModel.objects.filter(pk=listing.id).exists()
        assert not type(reservation).objects.filter(pk=reservation.id).exists()


def test_mine_lists_own_listings_including_hidden(client_for, make_user, make_hebergement):
    host = make_user(role='hote')
    make_hebergement(host=host, name='Visible')
    make_hebergement(host=host, name='Masqué', is_available=False)
    make_hebergement(name='Autre hôte')

    response = client_for(host).get(f'{HEBERGEMENTS}mine/')
    assert {h['name'] for h in response.data['results']} == {'Visible', 'Masqué'}
