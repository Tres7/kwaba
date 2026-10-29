import pytest

from apps.favoris.models import FavoriModel

FAVORIS = '/api/v1/favoris/'


def test_add_is_idempotent(client_for, make_user, make_hebergement):
    user, listing = make_user(), make_hebergement()
    client = client_for(user)

    assert client.post(FAVORIS, {'hebergement': str(listing.id)}, format='json').status_code == 201
    assert client.post(FAVORIS, {'hebergement': str(listing.id)}, format='json').status_code == 200
    assert FavoriModel.objects.filter(user_id=user.id, hebergement_id=listing.id).count() == 1


def test_unknown_listing(client_for, make_user):
    response = client_for(make_user()).post(FAVORIS, {'hebergement': '00000000-0000-0000-0000-000000000000'},
                                            format='json')
    assert response.status_code == 400


def test_remove(client_for, make_user, make_hebergement):
    user, listing = make_user(), make_hebergement()
    FavoriModel.objects.create(user_id=user.id, hebergement_id=listing.id)
    client = client_for(user)

    assert client.delete(f'{FAVORIS}{listing.id}/').status_code == 204
    assert client.delete(f'{FAVORIS}{listing.id}/').status_code == 404


def test_list_only_own_favorites(client_for, make_user, make_hebergement):
    user = make_user()
    mine = make_hebergement(name='Le mien')
    FavoriModel.objects.create(user_id=user.id, hebergement_id=mine.id)
    FavoriModel.objects.create(user_id=make_user().id, hebergement_id=make_hebergement(name='Pas le mien').id)

    results = client_for(user).get(FAVORIS).data['results']
    assert [f['hebergement'] for f in results] == [mine.id]


def test_anonymous_unauthorized(api_client):
    assert api_client.get(FAVORIS).status_code == 401


def test_unpublished_listing_cannot_be_added(client_for, make_user, make_hebergement):
    masquee = make_hebergement(is_available=False)
    response = client_for(make_user()).post(FAVORIS, {'hebergement': str(masquee.id)}, format='json')
    assert response.status_code == 400


@pytest.mark.parametrize('retrait', [
    lambda client_for, annonce: client_for(annonce.host).delete(f'/api/v1/hebergements/{annonce.id}/'),
    lambda client_for, annonce: type(annonce).objects.filter(pk=annonce.pk).update(is_available=False),
], ids=['archived', 'hidden'])
def test_listing_no_longer_public_leaves_the_list_but_the_favourite_is_kept(client_for, make_user, make_hebergement,
                                                                             retrait):
    user, annonce = make_user(), make_hebergement()
    FavoriModel.objects.create(user_id=user.id, hebergement_id=annonce.id)

    retrait(client_for, annonce)

    assert client_for(user).get(FAVORIS).data == {'results': [], 'count': 0}
    assert FavoriModel.objects.filter(user_id=user.id, hebergement_id=annonce.id).exists()


def test_list_card_is_the_listing_card(client_for, make_user, make_hebergement):
    user, annonce = make_user(), make_hebergement(name='Villa Océane')
    FavoriModel.objects.create(user_id=user.id, hebergement_id=annonce.id)

    carte = client_for(user).get(FAVORIS).data['results'][0]['hebergement_detail']

    assert (carte['id'], carte['name'], carte['host_id']) == (str(annonce.id), 'Villa Océane', str(annonce.host_id))


def test_query_count_does_not_grow_with_favourites(client_for, make_user, make_hebergement,
                                                   django_assert_max_num_queries):
    user = make_user()
    client = client_for(user)
    for i in range(8):
        FavoriModel.objects.create(user_id=user.id, hebergement_id=make_hebergement(name=f'Annonce {i}').id)

    with django_assert_max_num_queries(8):
        assert client.get(FAVORIS).data['count'] == 8
