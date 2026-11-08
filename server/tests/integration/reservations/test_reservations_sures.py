"""Bookings whose terms cannot move after payment, and that cannot be used to reach the host outside the platform
nor to hold a listing without paying (security audit of 2026-11-07, leads 13, 14, 15, 16, 21 and 22)."""
from datetime import time, timedelta

import pytest
from django.utils import timezone

from apps.hebergements.models import HebergementModel
from apps.hebergements.serializers import RechercheSerializer
from apps.paiements import tarifs
from apps.reservations import documents
from apps.reservations.models import ReservationModel
from apps.securite.models import AlerteFraudeModel

RESERVATIONS = '/api/v1/reservations/'
FEDAPAY_TEST = {'SECRET_KEY': 'sk_sandbox_test', 'ENV': 'sandbox', 'WEBHOOK_SECRET': '', 'EXPIRATION_MINUTES': 30}


def _reserver(client, hebergement, dans=10, nuits=2, **extra):
    debut = timezone.localdate() + timedelta(days=dans)
    return client.post(RESERVATIONS, {
        'hebergement': str(hebergement.id), 'check_in': debut.isoformat(),
        'check_out': (debut + timedelta(days=nuits)).isoformat(), 'guests_count': 1, **extra,
    }, format='json')


@pytest.fixture
def paiement_en_ligne(settings):
    """Online payment active: a booking waits for its payment."""
    settings.FEDAPAY = FEDAPAY_TEST
    settings.PAIEMENT_HORS_LIGNE = False


# --- Leads 13 and 14: the terms accepted at booking stay those of the booking ----------------------------------------

def test_politique_d_annulation_figee_a_la_reservation(client_for, make_user, make_hebergement):
    annonce = make_hebergement(politique_annulation='souple')
    r = _reserver(client_for(make_user()), annonce)
    assert r.status_code == 201, r.data

    # The host tightens the policy after the booking
    assert client_for(annonce.host).patch(f'/api/v1/hebergements/{annonce.id}/', {'politique_annulation': 'ferme'},
                                          format='json').status_code == 200
    resa = ReservationModel.objects.get(pk=r.data['id'])
    assert tarifs.politique(resa) == 'souple'
    assert tarifs.texte_politique(resa).startswith('Politique Souple')


class FauxDocument:
    """Records what the voucher writes, instead of the PDF."""
    lignes = []

    def __init__(self, *args, **kwargs):
        FauxDocument.lignes = []

    def bloc(self, titre, lignes):
        FauxDocument.lignes += lignes

    def montants(self, *args):
        pass

    def paragraphe(self, *args):
        pass

    def en_pdf(self):
        return b''


def test_horaires_et_petit_dejeuner_figes_sur_le_bon(client_for, make_user, make_hebergement, monkeypatch):
    annonce = make_hebergement(arrivee_a_partir=time(14), depart_avant=time(11), petit_dejeuner='option',
                               petit_dejeuner_prix=3000)
    r = _reserver(client_for(make_user()), annonce)
    assert r.status_code == 201, r.data
    HebergementModel.objects.filter(pk=annonce.pk).update(arrivee_a_partir=time(20), depart_avant=time(7),
                                                         petit_dejeuner='non')

    monkeypatch.setattr(documents, 'Document', FauxDocument)
    documents.bon(ReservationModel.objects.get(pk=r.data['id']))
    lignes = dict(FauxDocument.lignes)
    assert 'à partir de 14 h' in lignes['Arrivée']
    assert 'avant 11 h' in lignes['Départ']
    assert lignes['Petit-déjeuner'].startswith('en option')


# --- Lead 21: before payment, the host does not know who the traveller is ---------------------------------------------

def test_l_hote_ne_voit_pas_le_voyageur_avant_le_paiement(paiement_en_ligne, client_for, make_user, make_hebergement):
    annonce = make_hebergement()
    voyageur = make_user(first_name='Alice', last_name='Test')
    assert _reserver(client_for(voyageur), annonce, message="J'arrive en fin d'après-midi").status_code == 201

    vue = client_for(annonce.host).get(RESERVATIONS, {'as': 'host'}).data['results'][0]
    assert (vue['status'], vue['guest_name'], vue['message']) == ('pending', 'Voyageur', '')

    ReservationModel.objects.update(status='confirmed')  # paid
    vue = client_for(annonce.host).get(RESERVATIONS, {'as': 'host'}).data['results'][0]
    assert (vue['guest_name'], vue['message']) == ('Alice Test', "J'arrive en fin d'après-midi")

    # The traveller always sees their own booking whole
    assert client_for(voyageur).get(RESERVATIONS).data['results'][0]['message'] == "J'arrive en fin d'après-midi"


# --- Lead 22: the booking message follows the rules of the messaging --------------------------------------------------

def test_coordonnees_du_message_masquees_et_signalees(client_for, make_user, make_hebergement):
    voyageur = make_user()
    r = _reserver(client_for(voyageur), make_hebergement(), message='Appelez-moi au +228 90 12 34 56, merci')
    assert r.status_code == 201, r.data

    message = ReservationModel.objects.get(pk=r.data['id']).message
    assert '90 12 34 56' not in message and message.startswith('Appelez-moi au')
    alerte = AlerteFraudeModel.objects.get(utilisateur_id=voyageur.pk)
    assert (alerte.contexte, alerte.objet_id, alerte.types) == ('reservation', str(r.data['id']), ['telephone'])


def test_message_sans_coordonnees_inchange(client_for, make_user, make_hebergement):
    r = _reserver(client_for(make_user()), make_hebergement(), message='Arrivée vers 18 h,\navec deux valises.')
    assert ReservationModel.objects.get(pk=r.data['id']).message == 'Arrivée vers 18 h,\navec deux valises.'
    assert not AlerteFraudeModel.objects.exists()


# --- Lead 16: a listing cannot be held without paying ------------------------------------------------------------------

def test_au_plus_trois_reservations_en_attente(paiement_en_ligne, client_for, make_user, make_hebergement):
    client = client_for(make_user())
    for dans in (10, 20, 30):
        assert _reserver(client, make_hebergement(), dans=dans).status_code == 201

    r = _reserver(client, make_hebergement(), dans=40)
    assert r.status_code == 400
    assert 'en attente de paiement' in str(r.data)

    # An expired one frees a place
    ReservationModel.objects.filter(pk=ReservationModel.objects.first().pk).update(
        expire_le=timezone.now() - timedelta(minutes=1))
    assert _reserver(client, make_hebergement(), dans=40).status_code == 201


# --- Lead 15: a search does not compute availability over an unbounded stay -----------------------------------------

@pytest.mark.parametrize('debut, nuits', [(1, 30000), (1, 91), (-5, 3)], ids=['demesure', 'plus_de_90_nuits', 'passe'])
def test_recherche_ignore_un_sejour_impossible_a_reserver(api_client, make_hebergement, debut, nuits):
    jour = timezone.localdate() + timedelta(days=debut)
    params = {'check_in': jour.isoformat(), 'check_out': (jour + timedelta(days=nuits)).isoformat()}
    recherche = RechercheSerializer.depuis(params)
    assert recherche.is_valid()
    assert 'check_in' not in recherche.validated_data

    make_hebergement()
    assert api_client.get('/api/v1/hebergements/', params).status_code == 200


def test_recherche_garde_un_sejour_reservable(make_hebergement):
    jour = timezone.localdate() + timedelta(days=1)
    recherche = RechercheSerializer.depuis({'check_in': jour.isoformat(), 'check_out': (jour + timedelta(days=90)).isoformat()})
    assert recherche.is_valid() and recherche.validated_data['check_in'] == jour
