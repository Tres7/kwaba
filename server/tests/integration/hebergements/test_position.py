"""Position of a listing: exact for its host and the agents, approximate for everyone else."""
import math
from decimal import Decimal

import pytest

from apps.hebergements.models import HebergementModel
from apps.hebergements.positions import DISTANCE_MIN_M, METRES_PAR_DEGRE, ZONE_M, approchee
from apps.verifications.models import PieceIdentiteModel

HEBERGEMENTS = '/api/v1/hebergements/'
LATITUDE, LONGITUDE = Decimal('6.137500'), Decimal('1.212300')


def _annonce(**extra):
    return {
        'name': 'Villa Océane', 'type': 'villa', 'city': 'Lomé', 'location': 'Baguida', 'price_per_night': 85000,
        'max_guests': 6, 'surface_m2': 140, 'chambres': 3, 'lits_doubles': 2, 'petit_dejeuner': 'non',
        'latitude': '6.1375', 'longitude': '1.2123', **extra,
    }


def _distance_m(position) -> float:
    nord = (position['lat'] - float(LATITUDE)) * METRES_PAR_DEGRE
    est = (position['lng'] - float(LONGITUDE)) * METRES_PAR_DEGRE * math.cos(math.radians(float(LATITUDE)))
    return math.hypot(nord, est)


@pytest.fixture
def annonce(make_hebergement):
    return make_hebergement(latitude=LATITUDE, longitude=LONGITUDE)


class TestSaisie:
    def test_obligatoire_pour_une_nouvelle_annonce(self, client_for, make_user):
        client = client_for(make_user(role='hote', phone='+22890000001'))
        donnees = _annonce()
        del donnees['latitude'], donnees['longitude']

        reponse = client.post(HEBERGEMENTS, donnees, format='json')

        assert reponse.status_code == 400 and 'latitude' in reponse.data

    def test_une_seule_coordonnee_refusee(self, client_for, make_user):
        client = client_for(make_user(role='hote', phone='+22890000001'))
        donnees = _annonce()
        del donnees['longitude']

        assert client.post(HEBERGEMENTS, donnees, format='json').status_code == 400

    @pytest.mark.parametrize('champ, valeur', [('latitude', '86'), ('latitude', '-86'), ('longitude', '181'), ('longitude', 'ici')])
    def test_valeur_impossible_refusee(self, client_for, make_user, champ, valeur):
        client = client_for(make_user(role='hote', phone='+22890000001'))

        reponse = client.post(HEBERGEMENTS, _annonce(**{champ: valeur}), format='json')

        assert reponse.status_code == 400 and champ in reponse.data

    def test_hote_recoit_la_position_exacte(self, client_for, make_user):
        client = client_for(make_user(role='hote', phone='+22890000001'))

        reponse = client.post(HEBERGEMENTS, _annonce(), format='json')

        assert reponse.status_code == 201
        assert (Decimal(reponse.data['latitude']), Decimal(reponse.data['longitude'])) == (LATITUDE, LONGITUDE)


class TestLectureParLesVoyageurs:
    def test_liste_sans_position_exacte(self, api_client, annonce):
        ligne = api_client.get(HEBERGEMENTS).data['results'][0]

        assert 'latitude' not in ligne and 'longitude' not in ligne
        assert DISTANCE_MIN_M - 1 <= _distance_m(ligne['position']) <= ZONE_M + 1

    def test_fiche_sans_position_exacte(self, api_client, annonce):
        fiche = api_client.get(f'{HEBERGEMENTS}{annonce.id}/').data

        assert 'latitude' not in fiche and 'longitude' not in fiche
        assert DISTANCE_MIN_M - 1 <= _distance_m(fiche['position']) <= ZONE_M + 1

    def test_position_toujours_la_meme(self, api_client, annonce):
        premiere = api_client.get(f'{HEBERGEMENTS}{annonce.id}/').data['position']

        assert api_client.get(f'{HEBERGEMENTS}{annonce.id}/').data['position'] == premiere

    def test_chaque_annonce_a_son_decalage(self, make_hebergement):
        positions = [approchee(make_hebergement(latitude=LATITUDE, longitude=LONGITUDE)) for _ in range(5)]

        assert len({(p['lat'], p['lng']) for p in positions}) == 5

    def test_annonce_ancienne_sans_position(self, api_client, make_hebergement):
        annonce = make_hebergement()

        assert api_client.get(f'{HEBERGEMENTS}{annonce.id}/').data['position'] is None

    def test_agent_hors_mission_sans_position_exacte(self, client_for, make_user, annonce):
        fiche = client_for(make_user(role='agent')).get(f'{HEBERGEMENTS}{annonce.id}/').data

        assert 'latitude' not in fiche


class TestLectureParLHote:
    def test_fiche_et_liste_avec_la_position_exacte(self, client_for, annonce):
        client = client_for(annonce.host)

        assert Decimal(client.get(f'{HEBERGEMENTS}{annonce.id}/').data['latitude']) == LATITUDE
        assert Decimal(client.get(f'{HEBERGEMENTS}mine/').data['results'][0]['longitude']) == LONGITUDE


class TestFileDesVisites:
    def test_agent_recoit_la_position_exacte(self, client_for, make_user, make_hebergement):
        annonce = make_hebergement(latitude=LATITUDE, longitude=LONGITUDE, statut_verification='en_attente')
        PieceIdentiteModel.objects.create(hote_id=annonce.host_id, type_piece='cni', statut='verifiee')

        visite = client_for(make_user(role='agent')).get('/api/v1/verifications/visites/').data['results'][0]

        assert visite['position'] == {'lat': float(LATITUDE), 'lng': float(LONGITUDE)}

    def test_annonce_ancienne_sans_position(self, client_for, make_user, make_hebergement):
        annonce = make_hebergement(statut_verification='en_attente')
        PieceIdentiteModel.objects.create(hote_id=annonce.host_id, type_piece='cni', statut='verifiee')

        visite = client_for(make_user(role='agent')).get('/api/v1/verifications/visites/').data['results'][0]

        assert visite['position'] is None


class TestRemiseEnVerification:
    def test_deplacer_une_annonce_verifiee(self, client_for, annonce):
        reponse = client_for(annonce.host).patch(f'{HEBERGEMENTS}{annonce.id}/', {'latitude': '6.2', 'longitude': '1.3'}, format='json')

        assert reponse.status_code == 200
        annonce.refresh_from_db()
        assert annonce.statut_verification == 'en_attente'

    def test_renvoyer_la_meme_position(self, client_for, annonce):
        client_for(annonce.host).patch(f'{HEBERGEMENTS}{annonce.id}/', {'latitude': '6.1375', 'longitude': '1.2123'}, format='json')

        annonce.refresh_from_db()
        assert annonce.statut_verification == 'verifiee'

    def test_premiere_position_d_une_annonce_ancienne(self, client_for, make_hebergement):
        annonce = make_hebergement()

        client_for(annonce.host).patch(f'{HEBERGEMENTS}{annonce.id}/', {'latitude': '6.1375', 'longitude': '1.2123'}, format='json')

        annonce.refresh_from_db()
        assert annonce.statut_verification == 'verifiee' and annonce.latitude == LATITUDE

    def test_annonce_ancienne_modifiable_sans_position(self, client_for, make_hebergement):
        annonce = make_hebergement()

        reponse = client_for(annonce.host).patch(f'{HEBERGEMENTS}{annonce.id}/', {'name': 'Nouveau nom'}, format='json')

        assert reponse.status_code == 200 and HebergementModel.objects.get(pk=annonce.pk).latitude is None
