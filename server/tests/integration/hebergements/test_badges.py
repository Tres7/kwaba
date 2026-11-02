"""Badges of a listing seen by travellers: founder host (Founders Programme)."""
from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.paiements.models import ConditionsHoteModel

HEBERGEMENTS = '/api/v1/hebergements/'


@pytest.fixture
def founder(make_user):
    def _make(categorie='particulier', debut=date(2026, 11, 1), fin=date(2027, 4, 30)):
        host = make_user(role='hote')
        ConditionsHoteModel.objects.create(hote_id=host.pk, categorie=categorie, fondateur_debut=debut, fondateur_fin=fin)
        return host
    return _make


class TestFounderHost:
    def test_founder_badge_in_list_and_detail(self, api_client, make_hebergement, founder):
        listing = make_hebergement(host=founder())

        assert api_client.get(HEBERGEMENTS).data['results'][0]['hote_fondateur'] is True
        assert api_client.get(f'{HEBERGEMENTS}{listing.pk}/').data['hote_fondateur'] is True

    def test_title_kept_after_the_six_months_at_five_percent(self, api_client, make_hebergement, founder):
        listing = make_hebergement(host=founder(debut=date(2025, 1, 1), fin=date(2025, 6, 30)))

        assert api_client.get(f'{HEBERGEMENTS}{listing.pk}/').data['hote_fondateur'] is True

    def test_host_outside_the_programme(self, api_client, make_hebergement, make_user):
        host = make_user(role='hote')
        ConditionsHoteModel.objects.create(hote_id=host.pk, categorie='particulier')
        sans_conditions = make_hebergement(name='Studio Bè')
        avec_conditions = make_hebergement(host=host, name='Villa Baguida')

        assert api_client.get(f'{HEBERGEMENTS}{sans_conditions.pk}/').data['hote_fondateur'] is False
        assert api_client.get(f'{HEBERGEMENTS}{avec_conditions.pk}/').data['hote_fondateur'] is False

    def test_hotel_never_founder(self, api_client, make_hebergement, founder):
        listing = make_hebergement(host=founder(categorie='hotel'))

        assert api_client.get(f'{HEBERGEMENTS}{listing.pk}/').data['hote_fondateur'] is False

    def test_founders_read_once_for_a_page_of_results(self, api_client, make_hebergement, founder, make_user):
        for _ in range(3):
            make_hebergement(host=founder())
        make_hebergement(host=make_user(role='hote'))

        with CaptureQueriesContext(connection) as requetes:
            resultats = api_client.get(HEBERGEMENTS).data['results']

        assert sorted(r['hote_fondateur'] for r in resultats) == [False, True, True, True]
        assert sum('paiements_conditionshote' in q['sql'] for q in requetes.captured_queries) == 1
