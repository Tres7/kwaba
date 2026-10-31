"""Drafts of new listings: saved incomplete by their host, never a listing until submitted."""
import pytest

from apps.hebergements import brouillons
from apps.hebergements.models import BrouillonAnnonceModel, HebergementModel

BROUILLONS = '/api/v1/hebergements/brouillons/'
HEBERGEMENTS = '/api/v1/hebergements/'


def _annonce(**extra):
    return {
        'name': 'Villa Océane', 'type': 'villa', 'city': 'Lomé', 'location': 'Baguida', 'price_per_night': 85000,
        'max_guests': 6, 'surface_m2': 140, 'chambres': 3, 'lits_doubles': 2, 'petit_dejeuner': 'non',
        'latitude': '6.1375', 'longitude': '1.2123', **extra,
    }


@pytest.fixture
def hote(client_for, make_user):
    return client_for(make_user(role='hote', phone='+22890000001'))


class TestEnregistrement:
    def test_brouillon_incomplet_accepte_sans_creer_d_annonce(self, hote):
        reponse = hote.post(BROUILLONS, {'donnees': {'name': 'Studio Bè', 'city': 'Lomé'}}, format='json')

        assert reponse.status_code == 201
        assert reponse.data['donnees'] == {'name': 'Studio Bè', 'city': 'Lomé'}
        # Not a listing: no unit type, no visit, nothing for travellers or the host's listings
        assert not HebergementModel.tous.exists()
        assert hote.get(f'{HEBERGEMENTS}mine/').data['count'] == 0

    def test_seuls_les_champs_du_formulaire_sont_gardes(self, hote):
        reponse = hote.post(BROUILLONS, {'donnees': {
            'name': 'Studio Bè', 'statut_verification': 'verifiee', 'host_id': 'autre', 'inconnu': 1,
        }}, format='json')

        assert reponse.data['donnees'] == {'name': 'Studio Bè'}

    def test_reprise_et_mise_a_jour(self, hote):
        cree = hote.post(BROUILLONS, {'donnees': {'name': 'Studio Bè'}}, format='json').data

        hote.put(f"{BROUILLONS}{cree['id']}/", {'donnees': {'name': 'Studio Bè', 'price_per_night': 25000}}, format='json')

        liste = hote.get(BROUILLONS).data['results']
        assert [b['donnees'] for b in liste] == [{'name': 'Studio Bè', 'price_per_night': 25000}]

    def test_voyageur_refuse(self, client_for, make_user):
        voyageur = client_for(make_user(role='voyageur'))

        assert voyageur.post(BROUILLONS, {'donnees': {}}, format='json').status_code == 403

    def test_nombre_limite(self, hote, monkeypatch):
        monkeypatch.setattr(brouillons, 'MAX_BROUILLONS', 2)
        for _ in range(2):
            hote.post(BROUILLONS, {'donnees': {}}, format='json')

        assert hote.post(BROUILLONS, {'donnees': {}}, format='json').status_code == 400

    def test_taille_limitee(self, hote):
        reponse = hote.post(BROUILLONS, {'donnees': {'description': 'x' * (brouillons.TAILLE_MAX + 1)}}, format='json')

        assert reponse.status_code == 400 and 'donnees' in reponse.data


class TestAutreHote:
    def test_brouillon_invisible_et_intouchable(self, hote, client_for, make_user):
        cree = hote.post(BROUILLONS, {'donnees': {'name': 'Studio Bè'}}, format='json').data
        autre = client_for(make_user(role='hote', phone='+22890000002'))
        url = f"{BROUILLONS}{cree['id']}/"

        assert autre.get(BROUILLONS).data['results'] == []
        assert autre.get(url).status_code == 404
        assert autre.put(url, {'donnees': {}}, format='json').status_code == 404
        assert autre.delete(url).status_code == 404
        assert BrouillonAnnonceModel.objects.filter(pk=cree['id']).exists()


class TestSoumission:
    def test_annonce_creee_et_brouillon_supprime(self, hote):
        cree = hote.post(BROUILLONS, {'donnees': {'name': 'Villa Océane'}}, format='json').data

        reponse = hote.post(HEBERGEMENTS, _annonce(brouillon=cree['id']), format='json')

        assert reponse.status_code == 201
        assert not BrouillonAnnonceModel.objects.exists()

    def test_brouillon_garde_si_l_annonce_est_refusee(self, hote):
        cree = hote.post(BROUILLONS, {'donnees': {'name': 'Villa Océane'}}, format='json').data
        incomplete = _annonce(brouillon=cree['id'])
        del incomplete['surface_m2']

        assert hote.post(HEBERGEMENTS, incomplete, format='json').status_code == 400
        assert BrouillonAnnonceModel.objects.filter(pk=cree['id']).exists()

    def test_brouillon_d_un_autre_hote_jamais_supprime(self, hote, client_for, make_user):
        autre = client_for(make_user(role='hote', phone='+22890000002'))
        sien = autre.post(BROUILLONS, {'donnees': {'name': 'Case Agbodrafo'}}, format='json').data

        assert hote.post(HEBERGEMENTS, _annonce(brouillon=sien['id']), format='json').status_code == 201
        assert BrouillonAnnonceModel.objects.filter(pk=sien['id']).exists()

    def test_identifiant_invalide_sans_effet(self, hote):
        assert hote.post(HEBERGEMENTS, _annonce(brouillon='pas-un-uuid'), format='json').status_code == 201
