"""Drafts of new listings: saved incomplete by their host, never a listing until submitted."""
import pytest

from apps.hebergements import brouillons
from apps.hebergements.models import BrouillonAnnonceModel, HebergementModel

BROUILLONS = '/api/v1/hebergements/brouillons/'
HEBERGEMENTS = '/api/v1/hebergements/'


def _listing(**extra):
    return {
        'name': 'Villa Océane', 'type': 'villa', 'city': 'Lomé', 'location': 'Baguida', 'price_per_night': 85000,
        'max_guests': 6, 'point_repere': 'Derrière la pharmacie', 'salles_de_bain': 1, 'chambres': 3, 'lits_doubles': 2, 'petit_dejeuner': 'non',
        'latitude': '6.1375', 'longitude': '1.2123', **extra,
    }


@pytest.fixture
def host(client_for, make_user):
    return client_for(make_user(role='hote', phone='+22890000001'))


class TestSaving:
    def test_incomplete_draft_accepted_without_creating_a_listing(self, host):
        reponse = host.post(BROUILLONS, {'donnees': {'name': 'Studio Bè', 'city': 'Lomé'}}, format='json')

        assert reponse.status_code == 201
        assert reponse.data['donnees'] == {'name': 'Studio Bè', 'city': 'Lomé'}
        # Not a listing: no unit type, no visit, nothing for travellers or the host's listings
        assert not HebergementModel.tous.exists()
        assert host.get(f'{HEBERGEMENTS}mine/').data['count'] == 0

    def test_only_form_fields_are_kept(self, host):
        reponse = host.post(BROUILLONS, {'donnees': {
            'name': 'Studio Bè', 'statut_verification': 'verifiee', 'host_id': 'autre', 'inconnu': 1,
        }}, format='json')

        assert reponse.data['donnees'] == {'name': 'Studio Bè'}

    def test_resume_and_update(self, host):
        cree = host.post(BROUILLONS, {'donnees': {'name': 'Studio Bè'}}, format='json').data

        host.put(f"{BROUILLONS}{cree['id']}/", {'donnees': {'name': 'Studio Bè', 'price_per_night': 25000}}, format='json')

        liste = host.get(BROUILLONS).data['results']
        assert [b['donnees'] for b in liste] == [{'name': 'Studio Bè', 'price_per_night': 25000}]

    def test_traveller_refused(self, client_for, make_user):
        voyageur = client_for(make_user(role='voyageur'))

        assert voyageur.post(BROUILLONS, {'donnees': {}}, format='json').status_code == 403

    def test_number_limited(self, host, monkeypatch):
        monkeypatch.setattr(brouillons, 'MAX_BROUILLONS', 2)
        for _ in range(2):
            host.post(BROUILLONS, {'donnees': {}}, format='json')

        assert host.post(BROUILLONS, {'donnees': {}}, format='json').status_code == 400

    def test_size_limited(self, host):
        reponse = host.post(BROUILLONS, {'donnees': {'description': 'x' * (brouillons.TAILLE_MAX + 1)}}, format='json')

        assert reponse.status_code == 400 and 'donnees' in reponse.data


class TestOtherHost:
    def test_draft_invisible_and_untouchable(self, host, client_for, make_user):
        cree = host.post(BROUILLONS, {'donnees': {'name': 'Studio Bè'}}, format='json').data
        autre = client_for(make_user(role='hote', phone='+22890000002'))
        url = f"{BROUILLONS}{cree['id']}/"

        assert autre.get(BROUILLONS).data['results'] == []
        assert autre.get(url).status_code == 404
        assert autre.put(url, {'donnees': {}}, format='json').status_code == 404
        assert autre.delete(url).status_code == 404
        assert BrouillonAnnonceModel.objects.filter(pk=cree['id']).exists()


class TestSubmission:
    def test_listing_created_and_draft_deleted(self, host):
        cree = host.post(BROUILLONS, {'donnees': {'name': 'Villa Océane'}}, format='json').data

        reponse = host.post(HEBERGEMENTS, _listing(brouillon=cree['id']), format='json')

        assert reponse.status_code == 201
        assert not BrouillonAnnonceModel.objects.exists()

    def test_draft_kept_when_the_listing_is_refused(self, host):
        cree = host.post(BROUILLONS, {'donnees': {'name': 'Villa Océane'}}, format='json').data
        incomplete = _listing(brouillon=cree['id'])
        del incomplete['point_repere']

        assert host.post(HEBERGEMENTS, incomplete, format='json').status_code == 400
        assert BrouillonAnnonceModel.objects.filter(pk=cree['id']).exists()

    def test_another_hosts_draft_never_deleted(self, host, client_for, make_user):
        autre = client_for(make_user(role='hote', phone='+22890000002'))
        sien = autre.post(BROUILLONS, {'donnees': {'name': 'Case Agbodrafo'}}, format='json').data

        assert host.post(HEBERGEMENTS, _listing(brouillon=sien['id']), format='json').status_code == 201
        assert BrouillonAnnonceModel.objects.filter(pk=sien['id']).exists()

    def test_invalid_id_has_no_effect(self, host):
        assert host.post(HEBERGEMENTS, _listing(brouillon='pas-un-uuid'), format='json').status_code == 201


class TestAssistant:
    @pytest.fixture
    def brouillon(self, host):
        return host.post(BROUILLONS, {'donnees': {'city': 'Lomé', 'max_guests': 2}}, format='json').data

    def test_answers_of_a_screen_are_added_to_the_others(self, host, brouillon):
        reponse = host.patch(f"{BROUILLONS}{brouillon['id']}/", {'donnees': {'location': 'Agoè'}, 'etape': 'adresse'}, format='json')

        assert reponse.status_code == 200
        assert reponse.data['donnees'] == {'city': 'Lomé', 'max_guests': 2, 'location': 'Agoè'}
        assert reponse.data['etape'] == 'adresse'
        assert not HebergementModel.objects.exists()

    def test_screen_saved_alone(self, host, brouillon):
        reponse = host.patch(f"{BROUILLONS}{brouillon['id']}/", {'etape': 'photos'}, format='json')
        assert (reponse.data['etape'], reponse.data['donnees']['city']) == ('photos', 'Lomé')

    def test_answers_the_api_would_refuse_are_saved_and_reported(self, host, brouillon):
        reponse = host.patch(f"{BROUILLONS}{brouillon['id']}/", {'donnees': {'description': 'Appelez-moi au 90 00 00 01'}}, format='json')

        assert reponse.status_code == 200
        assert reponse.data['donnees']['description'] == 'Appelez-moi au 90 00 00 01'
        assert 'description' in reponse.data['erreurs']

    def test_incomplete_draft_is_not_an_error(self, host, brouillon):
        assert host.patch(f"{BROUILLONS}{brouillon['id']}/", {'donnees': {'name': 'Villa'}}, format='json').data['erreurs'] == {}

    def test_unknown_fields_and_values_refused(self, host, brouillon):
        adresse = f"{BROUILLONS}{brouillon['id']}/"
        assert 'host_id' not in host.patch(adresse, {'donnees': {'host_id': 'x'}}, format='json').data['donnees']
        assert host.patch(adresse, {'donnees': 'texte'}, format='json').status_code == 400
        assert host.patch(adresse, {'etape': '../admin'}, format='json').status_code == 400

    def test_other_host_cannot_change_a_draft(self, brouillon, client_for, make_user):
        autre = client_for(make_user(role='hote'))
        assert autre.patch(f"{BROUILLONS}{brouillon['id']}/", {'donnees': {'name': 'Pirate'}}, format='json').status_code == 404
        assert BrouillonAnnonceModel.objects.get(pk=brouillon['id']).donnees.get('name') is None

    def test_candidate_can_start_a_draft(self, client_for, make_user):
        candidat = client_for(make_user(candidature_hote='ouverte'))
        assert candidat.post(BROUILLONS, {'donnees': {}}, format='json').status_code == 201


class TestEspace:
    def test_follows_the_private_room_type(self, host):
        reponse = host.post(HEBERGEMENTS, _listing(type='chambre_privee', espace='entier'), format='json')

        assert reponse.data['espace'] == 'chambre_privee'
        annonce = HebergementModel.objects.get()
        assert annonce.types.get().nom == 'Chambre privée'

    def test_whole_place_for_the_other_types(self, host):
        assert host.post(HEBERGEMENTS, _listing(espace='chambre_privee'), format='json').data['espace'] == 'entier'

    def test_former_types_refused(self, host):
        assert host.post(HEBERGEMENTS, _listing(type='maison'), format='json').status_code == 400

    def test_search_filter(self, api_client, make_hebergement):
        make_hebergement(type='villa')
        chambre = make_hebergement(type='chambre_privee')

        resultats = api_client.get(HEBERGEMENTS, {'espace': 'chambre_privee'}).data['results']

        assert [r['id'] for r in resultats] == [str(chambre.pk)]
