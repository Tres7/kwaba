import pytest

from apps.avis.models import CRITERES, AvisModel

AVIS = '/api/v1/avis/'


def _review(reservation, note=4, **overrides):
    return {
        'reservation': str(reservation.id),
        'note': note,
        **{critere: note for critere in CRITERES},
        'commentaire': 'Séjour très agréable, hôte disponible et logement propre.',
        **overrides,
    }


def _make_avis(reservation, note):
    return AvisModel.objects.create(
        reservation_id=reservation.id, hebergement_id=reservation.hebergement_id, auteur=reservation.guest,
        note=note, **{critere: note for critere in CRITERES}, commentaire='Commentaire de test assez long.',
    )


@pytest.fixture
def listing(make_hebergement):
    return make_hebergement()


@pytest.fixture
def finished_stay(listing, make_reservation):
    return make_reservation(listing, starts_in=-5, nights=3)


class TestCreate:
    def test_review_updates_listing_rating(self, client_for, listing, finished_stay, make_reservation):
        _make_avis(make_reservation(listing, starts_in=-10, nights=2), note=5)

        response = client_for(finished_stay.guest).post(AVIS, _review(finished_stay, note=4), format='json')

        assert response.status_code == 201
        listing.refresh_from_db()
        assert (listing.rating, listing.review_count) == (4.5, 2)

    def test_future_stay_forbidden(self, client_for, listing, make_reservation):
        upcoming = make_reservation(listing, starts_in=5)
        assert client_for(upcoming.guest).post(AVIS, _review(upcoming), format='json').status_code == 403

    def test_other_user_forbidden(self, client_for, make_user, finished_stay):
        assert client_for(make_user()).post(AVIS, _review(finished_stay), format='json').status_code == 403

    def test_second_review_forbidden(self, client_for, finished_stay):
        client = client_for(finished_stay.guest)
        assert client.post(AVIS, _review(finished_stay), format='json').status_code == 201
        assert client.post(AVIS, _review(finished_stay), format='json').status_code == 403

    @pytest.mark.parametrize('overrides', [{'note': 6}, {'note': 0}, {'proprete': None}, {'commentaire': 'Trop court'}])
    def test_invalid_payload(self, client_for, finished_stay, overrides):
        payload = {k: v for k, v in _review(finished_stay, **overrides).items() if v is not None}
        assert client_for(finished_stay.guest).post(AVIS, payload, format='json').status_code == 400


class TestList:
    def test_public_summary_and_distribution(self, api_client, listing, make_reservation):
        for note in (5, 5, 3):
            _make_avis(make_reservation(listing, starts_in=-10, nights=2), note=note)

        data = api_client.get(AVIS, {'hebergement': str(listing.id)}).data
        assert data['resume']['total'] == 3
        assert data['resume']['moyenne'] == pytest.approx(4.33, abs=0.01)
        assert data['resume']['repartition'] == {5: 2, 4: 0, 3: 1, 2: 0, 1: 0}

    def test_pagination_bounds(self, api_client, listing, make_reservation):
        for _ in range(3):
            _make_avis(make_reservation(listing, starts_in=-10, nights=2), note=4)
        url_params = {'hebergement': str(listing.id)}

        assert len(api_client.get(AVIS, {**url_params, 'limit': 2}).data['results']) == 2
        assert len(api_client.get(AVIS, {**url_params, 'offset': -4}).data['results']) == 3
        assert len(api_client.get(AVIS, {**url_params, 'limit': 'abc'}).data['results']) == 3
        assert len(api_client.get(AVIS, {**url_params, 'limit': 0}).data['results']) == 3
        assert len(api_client.get(AVIS, {**url_params, 'limit': 500}).data['results']) == 3

    def test_unknown_listing(self, api_client):
        assert api_client.get(AVIS, {'hebergement': '00000000-0000-0000-0000-000000000000'}).status_code == 404

    def test_missing_listing_parameter(self, raw_client):
        assert raw_client.get(AVIS).status_code == 404

    def test_non_uuid_listing_parameter_is_not_a_server_error(self, raw_client):
        assert raw_client.get(AVIS, {'hebergement': 'abc'}).status_code in (400, 404)

    def test_negative_limit_is_not_a_server_error(self, raw_client, listing):
        assert raw_client.get(AVIS, {'hebergement': str(listing.id), 'limit': -5}).status_code == 200


class TestHostReply:
    def url(self, avis):
        return f'{AVIS}{avis.id}/reponse/'

    def test_host_replies_once(self, client_for, listing, finished_stay):
        avis = _make_avis(finished_stay, note=4)
        host = client_for(listing.host)

        response = host.post(self.url(avis), {'reponse': 'Merci pour votre visite !'}, format='json')
        assert response.status_code == 200
        assert response.data['reponse_le'] is not None
        assert host.post(self.url(avis), {'reponse': 'Encore merci'}, format='json').status_code == 409

    def test_other_user_forbidden(self, client_for, make_user, finished_stay):
        avis = _make_avis(finished_stay, note=4)
        response = client_for(make_user(role='hote')).post(self.url(avis), {'reponse': 'Bonjour'}, format='json')
        assert response.status_code == 403

    def test_empty_reply_rejected(self, client_for, listing, finished_stay):
        avis = _make_avis(finished_stay, note=4)
        assert client_for(listing.host).post(self.url(avis), {'reponse': ''}, format='json').status_code == 400


def test_rating_recomputed_when_review_deleted(listing, make_reservation):
    first = _make_avis(make_reservation(listing, starts_in=-10, nights=2), note=5)
    second = _make_avis(make_reservation(listing, starts_in=-20, nights=2), note=3)
    from apps.avis.services import recalculer_note
    recalculer_note(listing.id)

    first.delete()
    listing.refresh_from_db()
    assert (listing.rating, listing.review_count) == (3.0, 1)

    second.delete()
    listing.refresh_from_db()
    assert (listing.rating, listing.review_count) == (0.0, 0)


def test_stays_to_review(client_for, make_user, listing, make_reservation):
    guest = make_user()
    older = make_reservation(listing, guest=guest, starts_in=-12, nights=2)  # 14 days to review (review charter)
    recent = make_reservation(listing, guest=guest, starts_in=-5, nights=2)
    make_reservation(listing, guest=guest, starts_in=-100, nights=2)   # too late
    make_reservation(listing, guest=guest, starts_in=5, nights=2)      # upcoming
    _make_avis(make_reservation(listing, guest=guest, starts_in=-8, nights=1), note=4)  # already reviewed

    rows = client_for(guest).get(f'{AVIS}a-laisser/').data['results']
    assert [r['reservation_id'] for r in rows] == [str(recent.id), str(older.id)]


def test_booking_list_reads_reviews_once_whatever_their_number(client_for, make_user, listing, make_reservation,
                                                               django_assert_max_num_queries):
    voyageur = make_user()
    client = client_for(voyageur)
    _make_avis(make_reservation(listing, guest=voyageur, starts_in=-10, nights=2), note=5)
    client.get('/api/v1/reservations/')
    with django_assert_max_num_queries(50) as une:
        client.get('/api/v1/reservations/')

    for jours in (-20, -30, -40):
        _make_avis(make_reservation(listing, guest=voyageur, starts_in=jours, nights=2), note=4)
    with django_assert_max_num_queries(len(une.captured_queries)):
        lignes = client.get('/api/v1/reservations/').data['results']

    assert sum(1 for ligne in lignes if ligne['avis_id']) == 4
