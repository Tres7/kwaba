"""PDF documents: vouchers, receipts, invoices (continuous numbering, VAT), email attachments."""
from decimal import Decimal

import pytest
from django.core import mail
from django.core.files.storage import FileSystemStorage

from apps.documents.models import FactureModel, ParametresSocieteModel
from apps.give.models import DonModel, OrganisationModel
from apps.paiements import notifications
from apps.paiements.models import PaiementModel

D = '/api/v1/documents/'


@pytest.fixture(autouse=True)
def stockage(tmp_path, monkeypatch, settings):
    monkeypatch.setattr(FactureModel._meta.get_field('pdf'), 'storage', FileSystemStorage(location=tmp_path))
    settings.PAIEMENTS_PAUSE_EMAIL = 0


@pytest.fixture
def societe():
    return ParametresSocieteModel.objects.update_or_create(pk=1, defaults={
        'raison_sociale': 'Kwa-Ba SARL', 'adresse': 'Boulevard du 13 Janvier, Lomé', 'nif': '1000123456', 'rccm': 'TG-LOM-2026-B-1'})[0]


_n = iter(range(1, 1000))


def _paye(objet, montant, **champ):
    return PaiementModel.objects.create(montant=montant, statut='reussi', transaction_id=f'T{next(_n)}', **champ)


@pytest.fixture
def sejour(make_hebergement, make_reservation):
    r = make_reservation(make_hebergement(name='Villa Océane'), nights=3)
    r.prix_nuits, r.frais_service, r.total_price = 255000, 20400, 275400
    r.save()
    return r


def _pdf(reponse):
    assert reponse.status_code == 200, getattr(reponse, 'data', reponse)
    assert reponse['Content-Type'] == 'application/pdf'
    contenu = b''.join(reponse.streaming_content) if reponse.streaming else reponse.content
    assert contenu.startswith(b'%PDF')
    return contenu


def test_bon_et_recu_reserves_au_voyageur_apres_paiement(client_for, make_user, sejour):
    url = f'{D}reservation/{sejour.id}/'
    assert client_for(sejour.guest).get(url + 'bon/').status_code == 409  # not paid yet
    _paye(sejour, 275400, reservation=sejour)
    _pdf(client_for(sejour.guest).get(url + 'bon/'))
    _pdf(client_for(sejour.guest).get(url + 'recu/'))
    assert client_for(make_user()).get(url + 'bon/').status_code == 404
    _pdf(client_for(make_user(role='admin')).get(url + 'recu/'))
    assert client_for(sejour.guest).get(url + 'inconnu/').status_code == 404


def test_facture_numerotee_une_fois_par_sejour(client_for, sejour, make_hebergement, make_reservation, societe):
    _paye(sejour, 275400, reservation=sejour)
    url = f'{D}reservation/{sejour.id}/facture/'
    _pdf(client_for(sejour.guest).get(url))
    _pdf(client_for(sejour.guest).get(url))
    f = FactureModel.objects.get()
    assert f.numero.endswith('-00001') and f.total_ttc == 275400 and f.tva == 0
    autre = make_reservation(make_hebergement(), nights=2)
    autre.total_price = 50000
    autre.save()
    _paye(autre, 50000, reservation=autre)
    _pdf(client_for(autre.guest).get(f'{D}reservation/{autre.id}/facture/'))
    assert sorted(FactureModel.objects.values_list('numero', flat=True))[-1].endswith('-00002')


def test_facture_impossible_sans_informations_de_la_societe(client_for, sejour):
    _paye(sejour, 275400, reservation=sejour)
    reponse = client_for(sejour.guest).get(f'{D}reservation/{sejour.id}/facture/')
    assert reponse.status_code == 409 and 'raison sociale' in reponse.data['detail']


def test_tva_extraite_du_total(client_for, make_user, societe):
    societe.assujetti_tva, societe.taux_tva = True, Decimal('18')
    societe.save()
    admin = client_for(make_user(role='admin'))
    reponse = admin.post('/api/v1/admin/documents/factures/', {'client_nom': 'Hôtel du Golfe', 'lignes': [
        {'libelle': 'Campagne de visibilité', 'quantite': 1, 'prix_unitaire': 118000}]}, format='json')
    assert reponse.status_code == 201, reponse.data
    f = FactureModel.objects.get()
    assert (f.total_ht, f.tva, f.total_ttc) == (100000, 18000, 118000)
    _pdf(admin.get(f"/api/v1/admin/documents/factures/{f.id}/pdf/"))
    assert admin.get('/api/v1/admin/documents/factures/').data['count'] == 1


def test_informations_de_la_societe(client_for, make_user):
    admin = client_for(make_user(role='admin'))
    assert admin.get('/api/v1/admin/documents/societe/').data['complets'] is False
    reponse = admin.put('/api/v1/admin/documents/societe/', {'raison_sociale': 'Kwa-Ba SARL', 'adresse': 'Lomé'}, format='json')
    assert reponse.status_code == 200 and reponse.data['complets'] is True
    assert client_for(make_user()).get('/api/v1/admin/documents/societe/').status_code == 403


def test_email_de_confirmation_avec_bon_et_recu(sejour):
    paiement = _paye(sejour, 275400, reservation=sejour)
    notifications.reservation_payee_voyageur(paiement)
    noms = [a[0] for a in mail.outbox[-1].attachments if isinstance(a, tuple)]
    assert any(n.startswith('bon-') for n in noms) and any(n.startswith('recu-') for n in noms)


def test_recu_de_don(client_for, make_user):
    from django.utils import timezone
    ong = OrganisationModel.objects.create(nom='Écoles du Mono', slug='ecoles', cause='education', pays='TG', ville='Aného',
                                           resume='x', description='x', numero_enregistrement='TG-1')
    don = DonModel.objects.create(donateur=make_user(), organisation=ong, montant=2000, frais=60, total=2060, montant_ong=2000,
                                  statut='paye', paye_le=timezone.now())
    _paye(don, 2060, don=don)
    _pdf(client_for(don.donateur).get(f'{D}don/{don.id}/recu/'))
    assert client_for(don.donateur).get(f'{D}don/{don.id}/facture/').status_code == 404
