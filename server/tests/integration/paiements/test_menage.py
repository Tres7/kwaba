"""Cleaning fee by listing type (brief AN-TAX): added once to the stay, paid back in full to the host (no fee nor
commission on it), refunded when the traveller cancels."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.paiements import services, tarifs
from apps.paiements.models import FraisMenageModel, VersementModel
from apps.reservations.documents import lignes_facture
from apps.reservations.models import ReservationModel


@pytest.fixture(autouse=True)
def sans_paiement_en_ligne(settings):
    # Direct confirmation: the amounts are computed at creation
    settings.FEDAPAY = {**settings.FEDAPAY, 'SECRET_KEY': ''}
    settings.PAYPAL = {**settings.PAYPAL, 'CLIENT_ID': '', 'CLIENT_SECRET': ''}


def _reserver(client, hebergement, dans=20, nuits=2):
    debut = timezone.localdate() + timedelta(days=dans)
    r = client.post('/api/v1/reservations/', {'hebergement': str(hebergement.id), 'check_in': debut.isoformat(),
                                               'check_out': (debut + timedelta(days=nuits)).isoformat(), 'guests_count': 1})
    assert r.status_code == 201, r.data
    return ReservationModel.objects.get(pk=r.data['id'])


def test_default_scale_is_public(api_client):
    grille = api_client.get('/api/v1/paiements/config/').data['frais_menage']
    assert [grille[t] for t in ('chambre_privee', 'studio', 'appartement', 'maison_entiere', 'villa', 'chambre_hotel')] \
        == [3000, 5000, 7500, 10000, 15000, 0]
    assert grille['residence'] == grille['auberge'] == 0


def test_quote_adds_the_fee_without_fee_nor_commission_on_it(api_client, make_hebergement):
    studio = make_hebergement(type='studio', price_per_night=25000)
    devis = api_client.get(f'/api/v1/hebergements/{studio.id}/devis/', {'nuits': 2}).data
    # 6 % on the nights only
    assert (devis['prix_nuits'], devis['frais_service'], devis['frais_menage'], devis['total']) == (50000, 3000, 5000, 58000)


def test_booking_freezes_the_fee_and_the_host_gets_all_of_it(client_for, make_user, make_hebergement):
    villa = make_hebergement(type='villa', price_per_night=25000)
    resa = _reserver(client_for(make_user()), villa)
    assert (resa.prix_nuits, resa.frais_service, resa.commission_hote, resa.frais_menage) == (50000, 3000, 4000, 15000)
    assert resa.total_price == 68000 and resa.montant_hote == 61000

    # The team changes the scale: the booking keeps its amount
    FraisMenageModel.objects.filter(type_logement='villa').update(montant=20000)
    montants = client_for(resa.guest).get(f'/api/v1/reservations/{resa.id}/').data['montants']
    assert (montants['frais_menage'], montants['total'], montants['montant_hote']) == (15000, 68000, 61000)

    services.planifier_versement_hote(resa)
    versement = VersementModel.objects.get(reservation_id=resa.id)
    assert (versement.montant_brut, versement.commission, versement.montant) == (65000, 4000, 61000)


def test_scale_set_by_the_team(client_for, make_user, make_hebergement):
    FraisMenageModel.objects.filter(type_logement='appartement').update(montant=6000)
    resa = _reserver(client_for(make_user()), make_hebergement(type='appartement', price_per_night=25000))
    assert resa.frais_menage == 6000


def test_hotel_room_has_no_fee(client_for, make_user, make_hebergement):
    resa = _reserver(client_for(make_user()), make_hebergement(type='chambre_hotel', price_per_night=25000))
    assert resa.frais_menage == 0 and resa.total_price == 53000
    assert 'Frais de ménage' not in [ligne['libelle'] for ligne in lignes_facture(resa)]


def test_invoice_shows_the_fee(client_for, make_user, make_hebergement):
    resa = _reserver(client_for(make_user()), make_hebergement(type='studio', price_per_night=25000))
    lignes = lignes_facture(resa)
    assert {ligne['libelle']: ligne['prix_unitaire'] for ligne in lignes}['Frais de ménage'] == 5000
    assert sum(ligne['quantite'] * ligne['prix_unitaire'] for ligne in lignes) == resa.total_price


def test_cancellation_gives_the_fee_back():
    montants = tarifs.Montants(prix_nuits=50000, frais_service=3000, commission_hote=4000, frais_menage=5000)
    assert montants.total == 58000 and montants.montant_hote == 51000
    # Half of the nights kept: the traveller has not come, the cleaning fee is refunded
    moitie = tarifs._retenue(montants, 25000)
    assert (moitie.rembourse_voyageur, moitie.montant_hote) == (30000, 23000)
    tout = tarifs._retenue(montants, 50000)
    assert tout.rembourse_voyageur == 5000
