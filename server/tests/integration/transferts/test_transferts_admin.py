"""Transfers: driver assignment from the Django admin and API error cases."""
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

from apps.transferts.models import ChauffeurModel, TransfertModel

TRANSFERTS = '/api/v1/transferts/'


@pytest.fixture
def sans_paiement(settings):
    settings.FEDAPAY = {**settings.FEDAPAY, 'SECRET_KEY': ''}
    settings.PAYPAL = {'CLIENT_ID': '', 'CLIENT_SECRET': '', 'ENV': 'sandbox'}
    settings.PAIEMENTS_PAUSE_EMAIL = 0


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _transfert(client, **champs):
    jour = (timezone.localdate() + timedelta(days=5)).isoformat()
    r = client.post(TRANSFERTS, {'aeroport': 'LFW', 'arrivee': f'{jour}T14:30', 'numero_vol': 'AF520', 'passagers': 2,
                                 'bagages': 2, 'categorie': 'berline', 'destination': 'Villa, Lomé',
                                 'telephone': '+33 6 12 34 56 78', **champs}, format='json')
    assert r.status_code == 201, r.data
    return TransfertModel.objects.get(pk=r.data['id'])


def _chauffeur(categorie='berline'):
    c = ChauffeurModel.objects.create(prenom='Komi', nom='A.', telephone='+228 90 00 00 01', categorie=categorie,
                                      vehicule='Corolla', immatriculation='TG-1', pays_versement='TG',
                                      operateur_versement='togocel', numero_versement='90000001')
    c.aeroports.add('LFW')
    return c


def test_admin_attribue_le_chauffeur(sans_paiement, make_user):
    admin = make_user(role='admin', is_staff=True, is_superuser=True)
    t = _transfert(_client(make_user()))
    chauffeur = _chauffeur()
    navigateur = Client()
    navigateur.force_login(admin)
    url = f'/admin/transferts/transfertmodel/{t.id}/change/'
    page = navigateur.get(url)
    assert page.status_code == 200 and 'Komi' in page.content.decode()  # driver of this airport offered
    r = navigateur.post(url, {'chauffeur': chauffeur.pk, '_save': 'Enregistrer'}, follow=True)
    assert r.status_code == 200
    t.refresh_from_db()
    assert (t.statut, t.chauffeur_id) == ('chauffeur_assigne', chauffeur.pk)
    assert t.versement.montant == t.montant_chauffeur

    # Bulk action: cancel and refund
    r = navigateur.post('/admin/transferts/transfertmodel/', {'action': 'annuler_et_rembourser', '_selected_action': [t.pk]}, follow=True)
    t.refresh_from_db()
    assert t.statut == 'annule' and t.annule_par == 'plateforme'
    navigateur.post('/admin/transferts/transfertmodel/', {'action': 'annuler_et_rembourser', '_selected_action': [t.pk]}, follow=True)


def test_api_cas_d_erreur(sans_paiement, make_user):
    client = _client(make_user())
    anonyme = APIClient()
    jour = (timezone.localdate() + timedelta(days=5)).isoformat()
    assert anonyme.get(f'{TRANSFERTS}devis/', {'aeroport': 'XXX', 'arrivee': f'{jour}T10:00'}).status_code == 400
    assert anonyme.get(f'{TRANSFERTS}devis/', {'aeroport': 'LFW', 'arrivee': 'demain'}).status_code == 400
    assert anonyme.get(f'{TRANSFERTS}devis/', {'aeroport': 'LFW', 'arrivee': f'{jour}T10:00', 'passagers': 'deux'}).status_code == 400

    t = _transfert(client)
    assert t.statut == 'confirme'  # without online payment: confirmed directly
    assert client.get(f'{TRANSFERTS}?reservation=00000000-0000-0000-0000-000000000000').data['count'] == 0
    inconnu = '00000000-0000-0000-0000-000000000000'
    for methode, chemin in (('get', ''), ('delete', ''), ('post', 'payer/'), ('put', 'compte-remboursement/')):
        assert getattr(client, methode)(f'{TRANSFERTS}{inconnu}/{chemin}', {}, format='json').status_code == 404
    assert client.post(f'{TRANSFERTS}{t.id}/payer/', {'moyen': 'mobile_money'}, format='json').status_code == 400
    assert client.put(f'{TRANSFERTS}{t.id}/compte-remboursement/', {'pays': 'TG', 'operateur': 'togocel', 'numero': '90000001'},
                      format='json').status_code == 400  # no pending refund
    assert client.delete(f'{TRANSFERTS}{t.id}/').status_code == 200
    assert client.delete(f'{TRANSFERTS}{t.id}/').status_code == 400  # already cancelled

    # Another traveller's booking refused, unknown category at the airport
    autre = make_user()
    debut = timezone.localdate() + timedelta(days=30)
    from apps.reservations.models import ReservationModel
    from apps.hebergements.models import HebergementModel
    h = HebergementModel.objects.create(name='V', city='Lomé', price_per_night=10000, host_id=make_user(role='hote').pk, amenities=[])
    resa = ReservationModel.objects.create(hebergement_id=h.id, guest_id=autre.pk, check_in=debut, check_out=debut + timedelta(days=1), total_price=10800)
    r = client.post(TRANSFERTS, {'aeroport': 'LFW', 'arrivee': f'{jour}T14:30', 'numero_vol': 'AF520', 'passagers': 1, 'bagages': 1,
                                 'categorie': 'berline', 'destination': 'X', 'telephone': '+228 90 00 00 00', 'reservation': str(resa.id)},
                    format='json')
    assert r.status_code == 400 and 'reservation' in r.data
