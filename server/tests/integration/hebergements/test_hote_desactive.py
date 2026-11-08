"""Listings of a closed or banned host leave the site and can no longer be booked (security audit of
2026-11-07, lead 3). Nothing is deleted: reactivating the account brings them back."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

HEBERGEMENTS = '/api/v1/hebergements/'


@pytest.fixture
def annonce(make_hebergement):
    annonce = make_hebergement()
    get_user_model().objects.filter(pk=annonce.host_id).update(is_active=False)
    return annonce


def test_absente_de_la_recherche_et_de_sa_page(api_client, annonce):
    assert api_client.get(HEBERGEMENTS).data['results'] == []
    assert api_client.get(f'{HEBERGEMENTS}{annonce.id}/').status_code == 404


def test_non_reservable(client_for, make_user, annonce):
    debut = timezone.localdate() + timedelta(days=10)
    r = client_for(make_user()).post('/api/v1/reservations/', {
        'hebergement': str(annonce.id), 'check_in': debut.isoformat(),
        'check_out': (debut + timedelta(days=2)).isoformat(), 'guests_count': 1,
    }, format='json')
    assert r.status_code == 400


def test_revient_a_la_reactivation(api_client, annonce):
    get_user_model().objects.filter(pk=annonce.host_id).update(is_active=True)
    assert [h['id'] for h in api_client.get(HEBERGEMENTS).data['results']] == [str(annonce.id)]
