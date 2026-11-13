"""Position measured on site by the field agent at the visit: once the listing is validated, it replaces the point placed
by the host. Travellers still only get the offset position (150 to 400 m away)."""
import json
import math
from decimal import Decimal

import pytest

from apps.hebergements.models import HebergementModel
from apps.activity.models import ActivityEntryModel
from apps.verifications.models import PieceIdentiteModel, VisiteModel

TOUT_CONFORME = {'identite': True, 'adresse': True, 'photos': True, 'equipements': True}
POINT_HOTE = (Decimal('6.130000'), Decimal('1.220000'))
# About 1.1 km north of the host's point: what the agent measures in front of the house
SUR_PLACE = {'latitude': '6.140000', 'longitude': '1.220000', 'precision': '12.4'}


@pytest.fixture
def hote(make_user):
    hote = make_user(role='hote', phone='+22890000001')
    PieceIdentiteModel.objects.create(hote_id=hote.pk, type_piece='cni', statut='verifiee')
    return hote


@pytest.fixture
def annonce(make_hebergement, hote):
    return make_hebergement(host=hote, statut_verification='en_attente', location='Bè Kpota',
                            latitude=POINT_HOTE[0], longitude=POINT_HOTE[1])


@pytest.fixture
def agent(client_for, make_user):
    return client_for(make_user(role='agent'))


def _decider(agent, annonce, decision='validee', commentaire='', **position):
    donnees = {'decision': decision, 'controles': json.dumps(TOUT_CONFORME), 'commentaire': commentaire, **position}
    return agent.post(f'/api/v1/verifications/visites/{annonce.id}/decision/', donnees, format='multipart')


def _metres(a, b):
    lat1, lng1, lat2, lng2 = (math.radians(float(x)) for x in (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def test_la_position_de_l_agent_remplace_celle_de_l_hote(agent, annonce, api_client):
    reponse = _decider(agent, annonce, **SUR_PLACE)
    assert reponse.status_code == 201, reponse.data

    annonce.refresh_from_db()
    assert (annonce.latitude, annonce.longitude) == (Decimal('6.140000'), Decimal('1.220000'))
    assert annonce.statut_verification == 'verifiee'
    visite = VisiteModel.objects.get()
    assert visite.precision_m == 12 and 1100 <= visite.ecart_m <= 1125
    trace = ActivityEntryModel.objects.get(action='position_corrigee')
    assert trace.details['ecart_m'] == visite.ecart_m and trace.details['hebergement'] == str(annonce.id)

    # Travellers still get an offset position, around the agent's point (never the exact one)
    position = api_client.get(f'/api/v1/hebergements/{annonce.id}/').data['position']
    assert 140 <= _metres((position['lat'], position['lng']), (annonce.latitude, annonce.longitude)) <= 410


def test_sans_point_de_l_hote_la_position_de_l_agent_est_posee(agent, annonce):
    HebergementModel.objects.filter(pk=annonce.pk).update(latitude=None, longitude=None)
    assert _decider(agent, annonce, **SUR_PLACE).status_code == 201
    annonce.refresh_from_db()
    assert annonce.latitude == Decimal('6.140000') and VisiteModel.objects.get().ecart_m is None


def test_un_refus_garde_le_point_de_l_hote_mais_note_la_mesure(agent, annonce):
    reponse = _decider(agent, annonce, decision='refusee', commentaire="La maison n'existe pas à cette adresse.",
                       **SUR_PLACE)
    assert reponse.status_code == 201, reponse.data
    annonce.refresh_from_db()
    assert (annonce.latitude, annonce.longitude) == POINT_HOTE
    visite = VisiteModel.objects.get()
    assert visite.latitude == Decimal('6.140000') and visite.ecart_m is None
    assert not ActivityEntryModel.objects.filter(action='position_corrigee').exists()


def test_sans_mesure_le_point_de_l_hote_reste(agent, annonce):
    assert _decider(agent, annonce).status_code == 201
    annonce.refresh_from_db()
    assert (annonce.latitude, annonce.longitude) == POINT_HOTE and VisiteModel.objects.get().latitude is None


@pytest.mark.parametrize('position', [
    {**SUR_PLACE, 'precision': '480'},          # GPS not fixed yet (indoors): would mislead the travellers
    {**SUR_PLACE, 'latitude': '120'},           # out of range
    {**SUR_PLACE, 'longitude': 'abc'},          # unreadable
    {'latitude': '6.14', 'precision': '10'},    # half a position
])
def test_une_mesure_douteuse_est_refusee_sans_rien_changer(agent, annonce, position):
    reponse = _decider(agent, annonce, **position)
    assert reponse.status_code == 400 and 'osition' in reponse.data['detail']
    annonce.refresh_from_db()
    assert annonce.statut_verification == 'en_attente' and (annonce.latitude, annonce.longitude) == POINT_HOTE
    assert not VisiteModel.objects.exists()
