"""Quote of a stay: the amounts the site shows are the ones the booking computes again."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.hebergements.models import HebergementModel, TypeLogementModel
from apps.reservations.models import ReservationModel

HEBERGEMENTS = '/api/v1/hebergements/'
RESERVATIONS = '/api/v1/reservations/'


def _devis(client, annonce, **params):
    return client.get(f'{HEBERGEMENTS}{annonce.id}/devis/', params)


@pytest.fixture
def annonce(make_hebergement):
    return make_hebergement(price_per_night=25000)


class TestDevis:
    def test_montants_d_un_visiteur(self, api_client, annonce):
        r = _devis(api_client, annonce, nuits=2)
        assert r.status_code == 200
        assert r.data == {'prix_nuits': 50000, 'frais_service': 3000, 'total': 53000}

    def test_type_et_nombre_d_unites(self, api_client, annonce):
        suite = TypeLogementModel.objects.create(hebergement=annonce, nom='Suite', prix_nuit=40000, quantite=3, capacite=2)
        r = _devis(api_client, annonce, nuits=2, type_logement=str(suite.id), nb_unites=3)
        assert r.data == {'prix_nuits': 240000, 'frais_service': 14400, 'total': 254400}

    def test_le_total_est_accepte_par_la_reservation(self, client_for, make_user, annonce):
        voyageur = client_for(make_user())
        arrivee = timezone.localdate() + timedelta(days=10)
        devis = _devis(voyageur, annonce, nuits=3).data
        r = voyageur.post(RESERVATIONS, {
            'hebergement': str(annonce.id), 'check_in': arrivee.isoformat(), 'check_out': (arrivee + timedelta(days=3)).isoformat(),
            'guests_count': 1, 'payment_method': 'mobile_money', 'total_attendu': devis['total'],
        }, format='json')
        assert r.status_code == 201, r.data
        assert ReservationModel.objects.get(pk=r.data['id']).total_price == devis['total']

    def test_tarif_client_fidele(self, client_for, make_user, annonce, monkeypatch):
        voyageur = make_user()
        monkeypatch.setattr('apps.paiements.tarifs.hotes_deja_visites', lambda v: {annonce.host_id} if v == voyageur else set())
        r = _devis(client_for(voyageur), annonce, nuits=2)
        assert r.data == {'prix_nuits': 50000, 'frais_service': 1500, 'total': 51500}

    @pytest.mark.parametrize('params', [
        {}, {'nuits': 0}, {'nuits': 91}, {'nuits': 'x'},
        {'nuits': 2, 'nb_unites': 0}, {'nuits': 2, 'nb_unites': 2}, {'nuits': 2, 'nb_unites': 'x'},
        {'nuits': 2, 'type_logement': 'pas-un-uuid'}, {'nuits': 2, 'type_logement': '00000000-0000-0000-0000-000000000000'},
    ])
    def test_parametres_invalides(self, api_client, annonce, params):
        assert _devis(api_client, annonce, **params).status_code == 400

    def test_type_d_une_autre_annonce_refuse(self, api_client, annonce, make_hebergement):
        autre = TypeLogementModel.objects.filter(hebergement=make_hebergement()).first()
        assert _devis(api_client, annonce, nuits=2, type_logement=str(autre.id)).status_code == 400

    def test_annonce_non_publiee(self, api_client, client_for, make_hebergement):
        cachee = make_hebergement()
        HebergementModel.objects.filter(pk=cachee.pk).update(statut_verification='en_attente')
        assert _devis(api_client, cachee, nuits=2).status_code == 404
        assert _devis(client_for(cachee.host), cachee, nuits=2).status_code == 200

    def test_annonce_inconnue(self, api_client):
        assert api_client.get(f'{HEBERGEMENTS}00000000-0000-0000-0000-000000000000/devis/?nuits=2').status_code == 404
