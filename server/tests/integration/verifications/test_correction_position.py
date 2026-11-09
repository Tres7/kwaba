"""Position of a listing already verified, corrected by an agent or an admin from the agent space: with the phone's GPS
on site, or from a pasted Google Maps link, WhatsApp location or coordinates. The listing stays online."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.hebergements.models import HebergementModel
from apps.securite.models import JournalAuditModel

POSITIONS = '/api/v1/verifications/positions/'
POINT_HOTE = (Decimal('6.130000'), Decimal('1.220000'))


@pytest.fixture
def annonce(make_hebergement):
    return make_hebergement(name='Villa des cocotiers', city='Lomé', location='Bè Kpota',
                            latitude=POINT_HOTE[0], longitude=POINT_HOTE[1])


@pytest.fixture
def agent(client_for, make_user):
    return client_for(make_user(role='agent'))


def _corriger(client, annonce, **donnees):
    return client.post(f'{POSITIONS}{annonce.id}/', donnees, format='json')


def test_liste_des_annonces_a_relever(agent, annonce, make_hebergement):
    make_hebergement(name='En attente', statut_verification='en_attente', latitude=6.2, longitude=1.2)
    reponse = agent.get(POSITIONS)
    assert reponse.status_code == 200
    assert reponse.data['a_relever'] == 1 and [a['name'] for a in reponse.data['results']] == ['Villa des cocotiers']
    assert reponse.data['results'][0]['position'] == {'lat': 6.13, 'lng': 1.22}
    assert agent.get(POSITIONS, {'q': 'cocotiers'}).data['results'][0]['id'] == str(annonce.id)
    assert agent.get(POSITIONS, {'q': 'introuvable'}).data['results'] == []


def test_coordonnees_collees_remplacent_le_point_et_l_annonce_reste_en_ligne(agent, annonce, api_client):
    lu = agent.post(f'{POSITIONS}lire/', {'texte': 'https://maps.google.com/maps?q=6.1400%2C1.2200&z=17'}, format='json')
    assert lu.status_code == 200 and lu.data == {'latitude': 6.14, 'longitude': 1.22}

    reponse = _corriger(agent, annonce, **lu.data, source='texte')
    assert reponse.status_code == 200, reponse.data
    assert 1100 <= reponse.data['ecart_m'] <= 1125 and reponse.data['precision_m'] is None

    annonce.refresh_from_db()
    assert (annonce.latitude, annonce.longitude) == (Decimal('6.140000'), Decimal('1.220000'))
    assert annonce.statut_verification == 'verifiee' and annonce.position_relevee_le
    assert [h['id'] for h in api_client.get('/api/v1/hebergements/').data['results']] == [str(annonce.id)]
    trace = JournalAuditModel.objects.get(action='position_corrigee')
    assert trace.details == {'hebergement': str(annonce.id), 'source': 'texte', 'ecart_m': reponse.data['ecart_m'],
                             'precision_m': None}
    # Done: no longer in the list of positions to measure
    assert agent.get(POSITIONS).data['a_relever'] == 0
    assert agent.get(POSITIONS, {'toutes': '1'}).data['results'][0]['position_relevee_le']


def test_gps_sur_place(agent, annonce):
    assert _corriger(agent, annonce, latitude=6.14, longitude=1.22, precision=9.6, source='gps').data['precision_m'] == 10
    assert _corriger(agent, annonce, latitude=6.14, longitude=1.22, precision=480, source='gps').status_code == 400
    assert _corriger(agent, annonce, latitude=6.14, longitude=1.22, precision=None, source='gps').status_code == 400


def test_un_administrateur_corrige_aussi(client_for, make_user, annonce):
    admin = client_for(make_user(role='admin', is_staff=True))
    assert _corriger(admin, annonce, latitude=6.14, longitude=1.22, source='texte').status_code == 200


@pytest.mark.parametrize('donnees', [
    {'latitude': 120, 'longitude': 1.22, 'source': 'texte'},
    {'latitude': 'abc', 'longitude': 1.22, 'source': 'texte'},
    {'latitude': 6.14, 'longitude': 1.22, 'source': 'devine'},
])
def test_correction_invalide_ne_change_rien(agent, annonce, donnees):
    assert _corriger(agent, annonce, **donnees).status_code == 400
    annonce.refresh_from_db()
    assert (annonce.latitude, annonce.longitude) == POINT_HOTE and annonce.position_relevee_le is None


def test_annonce_non_verifiee_passe_par_la_visite(agent, make_hebergement):
    en_attente = make_hebergement(statut_verification='en_attente', latitude=6.2, longitude=1.2)
    assert _corriger(agent, en_attente, latitude=6.14, longitude=1.22, source='texte').status_code == 400


def test_personne_ne_corrige_sa_propre_annonce(client_for, annonce):
    get_user_model().objects.filter(pk=annonce.host_id).update(role='agent')
    hote_devenu_agent = client_for(get_user_model().objects.get(pk=annonce.host_id))
    assert _corriger(hote_devenu_agent, annonce, latitude=6.14, longitude=1.22, source='texte').status_code == 400


def test_reserve_aux_agents(client_for, make_user, annonce, api_client):
    voyageur = client_for(make_user())
    assert voyageur.get(POSITIONS).status_code == 403
    assert voyageur.post(f'{POSITIONS}lire/', {'texte': '6.1319, 1.2228'}, format='json').status_code == 403
    assert _corriger(voyageur, annonce, latitude=6.14, longitude=1.22, source='texte').status_code == 403
    assert api_client.get(POSITIONS).status_code in (401, 403)


def test_texte_illisible_explique(agent):
    reponse = agent.post(f'{POSITIONS}lire/', {'texte': 'Derrière la pharmacie'}, format='json')
    assert reponse.status_code == 400 and 'Google Maps' in reponse.data['detail']


def test_l_hote_qui_deplace_le_point_releve_le_rend_a_relever(agent, annonce, client_for):
    _corriger(agent, annonce, latitude=6.14, longitude=1.22, source='texte')
    hote = client_for(get_user_model().objects.get(pk=annonce.host_id))

    # Editing something else keeps the agent's point
    assert hote.patch(f'/api/v1/hebergements/{annonce.id}/', {'description': 'Calme', 'latitude': 6.14,
                                                              'longitude': 1.22}, format='json').status_code == 200
    annonce.refresh_from_db()
    assert annonce.position_relevee_le and annonce.statut_verification == 'verifiee'

    assert hote.patch(f'/api/v1/hebergements/{annonce.id}/', {'latitude': 6.15, 'longitude': 1.22},
                      format='json').status_code == 200
    annonce = HebergementModel.objects.get(pk=annonce.pk)
    assert annonce.position_relevee_le is None and annonce.statut_verification == 'en_attente'
