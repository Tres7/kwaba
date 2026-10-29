"""Additional payment paths: worker, payout failures, PayPal refunds, cancellations."""
from datetime import timedelta
from unittest import mock

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.paiements import fedapay, paypal, services
from apps.paiements.models import PaiementModel, ProfilVersementModel, RemboursementModel, VersementModel
from apps.reservations.models import ReservationModel
from apps.reservations import paiement as reservations_paiement

FEDAPAY_TEST = {'SECRET_KEY': 'sk_sandbox_test', 'ENV': 'sandbox', 'WEBHOOK_SECRET': '', 'EXPIRATION_MINUTES': 30}


class Faux:
    """Simulated FedaPay and PayPal, adjustable test by test."""

    def __init__(self):
        self.transaction = 'approved'
        self.payout_statut = 'sent'
        self.payout_erreur = None
        self.commande = 'COMPLETED'
        self.remboursement = 'PENDING'
        self.payouts = []

    # FedaPay
    def creer_transaction(self, **kwargs):
        return '501', 'https://sandbox-process.fedapay.com/501'

    def lire_transaction(self, identifiant):
        return {'id': identifiant, 'status': self.transaction, 'mode': 'momo_test',
                'customer': {'phone_number': {'number': '90000009', 'country': 'tg'}}}

    def creer_versement(self, **kwargs):
        if self.payout_erreur:
            raise fedapay.FedaPayErreur(self.payout_erreur)
        self.payouts.append(kwargs)
        return f'P{len(self.payouts)}'

    def lire_versement(self, identifiant):
        return {'id': identifiant, 'status': self.payout_statut, 'last_error_code': 'invalid_number'}

    # PayPal
    def creer_commande(self, **kwargs):
        return 'ORD9', 'https://paypal/payer'

    def lire_commande(self, identifiant):
        return {'id': identifiant, 'status': self.commande,
                'purchase_units': [{'payments': {'captures': [{'id': 'CAP9'}]}}]}

    def capturer(self, identifiant):
        return self.lire_commande(identifiant)

    def rembourser(self, capture, montant_eur, reference):
        return {'id': 'REF9', 'status': self.remboursement}

    def lire_remboursement(self, identifiant):
        return {'id': identifiant, 'status': self.remboursement}


@pytest.fixture
def faux(settings, monkeypatch):
    settings.FEDAPAY = FEDAPAY_TEST
    settings.PAYPAL = {'CLIENT_ID': 'id', 'CLIENT_SECRET': 'secret', 'ENV': 'sandbox'}
    settings.PAIEMENTS_PAUSE_EMAIL = 0
    f = Faux()
    monkeypatch.setattr(fedapay, 'client', mock.Mock(return_value=f))
    monkeypatch.setattr(paypal, 'client', mock.Mock(return_value=f))
    return f


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _reservation_payee(client, hebergement, moyen='mobile_money', dans=10):
    debut = timezone.localdate() + timedelta(days=dans)
    r = client.post('/api/v1/reservations/', {'hebergement': str(hebergement.id), 'check_in': debut.isoformat(),
                                              'check_out': (debut + timedelta(days=2)).isoformat(), 'guests_count': 1},
                    format='json')
    assert r.status_code == 201, r.data
    assert client.post(f"/api/v1/paiements/reservations/{r.data['id']}/payer/", {'moyen': moyen}, format='json').status_code == 200
    client.get(f"/api/v1/paiements/reservations/{r.data['id']}/statut/")
    return ReservationModel.objects.get(pk=r.data['id'])


def test_worker_une_passe(faux, make_user, make_hebergement, monkeypatch):
    # The worker closes stale connections at every pass: to neutralise in the test transaction
    monkeypatch.setattr('apps.paiements.management.commands.traiter_paiements.close_old_connections', lambda: None)
    hote = make_user(role='hote')
    voyageur = _client(make_user())
    resa = _reservation_payee(voyageur, make_hebergement(host=hote))
    ProfilVersementModel.objects.create(hote_id=hote.pk, pays='TG', operateur='togocel', numero='90000001', titulaire='Ama Hote')
    VersementModel.objects.filter(reservation_id=resa.id).update(date_prevue=timezone.now() - timedelta(minutes=1))

    call_command('traiter_paiements', '--once')  # sending of the payout
    call_command('traiter_paiements', '--once')  # FedaPay confirms: paid, email to the host
    v = VersementModel.objects.get(reservation_id=resa.id)
    assert v.statut == 'envoye' and v.notifie
    assert any('Versement de' in m.subject for m in mail.outbox)


def test_versement_refuse_puis_echoue_et_alerte(faux, make_user, make_hebergement):
    make_user(role='admin', email='admin@test.kwaba')
    hote = make_user(role='hote')
    resa = _reservation_payee(_client(make_user()), make_hebergement(host=hote))
    ProfilVersementModel.objects.create(hote_id=hote.pk, pays='TG', operateur='togocel', numero='90000001', titulaire='Ama')
    v = VersementModel.objects.get(reservation_id=resa.id)
    VersementModel.objects.filter(pk=v.pk).update(date_prevue=timezone.now() - timedelta(minutes=1), tentatives=services.MAX_TENTATIVES - 1,
                                                  mis_a_jour_le=timezone.now() - timedelta(days=1))

    faux.payout_erreur = 'Opération non autorisée'
    services.envoyer_versements_dus()
    v.refresh_from_db()
    assert (v.statut, v.derniere_erreur) == ('echoue', 'Opération non autorisée')
    from apps.paiements import notifications
    notifications.envoyer_notifications()
    assert any('Versement à un hôte à traiter' in m.subject for m in mail.outbox)


def test_versement_signale_en_echec_par_fedapay_puis_webhook(faux, make_user, make_hebergement):
    hote = make_user(role='hote')
    resa = _reservation_payee(_client(make_user()), make_hebergement(host=hote))
    v = VersementModel.objects.get(reservation_id=resa.id)
    VersementModel.objects.filter(pk=v.pk).update(statut='en_cours', payout_id='P7', tentatives=1)
    faux.payout_statut = 'failed'
    services.traiter_evenement({'name': 'payout.failed', 'entity': {'id': 'P7'}})
    v.refresh_from_db()
    assert (v.statut, v.derniere_erreur) == ('planifie', 'invalid_number')  # new try scheduled
    services.traiter_evenement({'name': 'payout.sent', 'entity': {}})  # without an id: ignored


def test_remboursement_paypal_en_attente_puis_confirme(faux, make_user, make_hebergement):
    voyageur = _client(make_user())
    resa = _reservation_payee(voyageur, make_hebergement(), moyen='paypal')
    assert resa.status == 'confirmed'
    voyageur.delete(f'/api/v1/reservations/{resa.id}/')
    services.envoyer_remboursements()
    rb = RemboursementModel.objects.get(reservation_id=resa.id)
    assert (rb.statut, rb.payout_id) == ('en_cours', 'REF9')
    faux.remboursement = 'COMPLETED'
    services.passe()
    rb.refresh_from_db()
    assert rb.statut == 'envoye' and rb.notifie
    assert any('Remboursement de' in m.subject and 'PayPal' in m.body for m in mail.outbox)


def test_remboursement_paypal_refuse_et_sans_capture(faux, make_user, make_hebergement):
    voyageur = _client(make_user())
    resa = _reservation_payee(voyageur, make_hebergement(), moyen='paypal')
    voyageur.delete(f'/api/v1/reservations/{resa.id}/')
    rb = RemboursementModel.objects.get(reservation_id=resa.id)
    RemboursementModel.objects.filter(pk=rb.pk).update(statut='en_cours', payout_id='REF9')
    faux.remboursement = 'FAILED'
    services.synchroniser_remboursement(RemboursementModel.objects.get(pk=rb.pk))
    assert RemboursementModel.objects.get(pk=rb.pk).statut == 'a_traiter'

    PaiementModel.objects.filter(pk=rb.paiement_id).update(capture_id='')
    RemboursementModel.objects.filter(pk=rb.pk).update(statut='a_envoyer')
    services.envoyer_remboursements()
    assert RemboursementModel.objects.get(pk=rb.pk).statut == 'a_traiter'


def test_remboursement_mobile_money_suivi_par_fedapay(faux, make_user, make_hebergement):
    voyageur = _client(make_user())
    resa = _reservation_payee(voyageur, make_hebergement())
    assert PaiementModel.objects.get(reservation_id=resa.id).telephone == '90000009'
    voyageur.delete(f'/api/v1/reservations/{resa.id}/')
    services.envoyer_remboursements()
    rb = RemboursementModel.objects.get(reservation_id=resa.id)
    assert rb.statut == 'en_cours'
    faux.payout_statut = 'failed'
    services.traiter_evenement({'name': 'payout.failed', 'entity': {'id': rb.payout_id}})
    assert RemboursementModel.objects.get(pk=rb.pk).statut == 'a_traiter'


def test_annulation_par_l_hote_rembourse_tout(faux, make_user, make_hebergement):
    resa = _reservation_payee(_client(make_user()), make_hebergement(), dans=3)
    assert reservations_paiement.annuler(resa, par='hote') == resa.total_price
    assert VersementModel.objects.get(reservation_id=resa.id).statut == 'annule'
    with pytest.raises(services.PaiementErreur):
        reservations_paiement.annuler(resa, par='plateforme')


def test_demarrer_paiement_refuse(faux, make_user, make_hebergement, settings):
    voyageur = _client(make_user())
    resa = _reservation_payee(voyageur, make_hebergement())
    url = f'/api/v1/paiements/reservations/{resa.id}/payer/'
    assert voyageur.post(url, {'moyen': 'mobile_money'}, format='json').status_code == 400  # already confirmed
    assert voyageur.post('/api/v1/paiements/reservations/00000000-0000-0000-0000-000000000000/payer/').status_code == 404

    faux.transaction = 'pending'
    debut = timezone.localdate() + timedelta(days=40)
    r = voyageur.post('/api/v1/reservations/', {'hebergement': str(make_hebergement().id), 'check_in': debut.isoformat(),
                                                 'check_out': (debut + timedelta(days=1)).isoformat()}, format='json')
    ReservationModel.objects.filter(pk=r.data['id']).update(expire_le=timezone.now() - timedelta(minutes=1))
    expiree = voyageur.post(f"/api/v1/paiements/reservations/{r.data['id']}/payer/", {'moyen': 'mobile_money'}, format='json')
    assert expiree.status_code == 400 and 'délai' in expiree.data['detail']

    faux.creer_transaction = mock.Mock(side_effect=fedapay.FedaPayErreur('panne'))
    ReservationModel.objects.filter(pk=r.data['id']).update(expire_le=timezone.now() + timedelta(minutes=10))
    panne = voyageur.post(f"/api/v1/paiements/reservations/{r.data['id']}/payer/", {'moyen': 'carte'}, format='json')
    assert panne.status_code == 400 and 'indisponible' in panne.data['detail']
    faux.creer_commande = mock.Mock(side_effect=paypal.PayPalErreur('panne'))
    assert 'PayPal' in voyageur.post(f"/api/v1/paiements/reservations/{r.data['id']}/payer/", {'moyen': 'paypal'},
                                     format='json').data['detail']


def test_paiement_refuse_ou_annule_chez_le_prestataire(faux, make_user, make_hebergement):
    voyageur = _client(make_user())
    debut = timezone.localdate() + timedelta(days=50)
    r = voyageur.post('/api/v1/reservations/', {'hebergement': str(make_hebergement().id), 'check_in': debut.isoformat(),
                                                 'check_out': (debut + timedelta(days=1)).isoformat()}, format='json')
    faux.transaction = 'declined'
    voyageur.post(f"/api/v1/paiements/reservations/{r.data['id']}/payer/", {'moyen': 'mobile_money'}, format='json')
    assert voyageur.get(f"/api/v1/paiements/reservations/{r.data['id']}/statut/").data['paiement'] == 'echoue'

    faux.commande = 'VOIDED'
    voyageur.post(f"/api/v1/paiements/reservations/{r.data['id']}/payer/", {'moyen': 'paypal'}, format='json')
    assert voyageur.get(f"/api/v1/paiements/reservations/{r.data['id']}/statut/").data['paiement'] == 'annule'


def test_config_et_revenus(faux, make_user, make_hebergement):
    config = APIClient().get('/api/v1/paiements/config/').data
    assert config['actif'] and config['moyens'] == ['mobile_money', 'carte', 'paypal']
    hote = make_user(role='hote')
    _reservation_payee(_client(make_user()), make_hebergement(host=hote))
    revenus = _client(hote).get('/api/v1/paiements/revenus/').data
    assert revenus['totaux']['a_venir'] > 0 and not revenus['profil_complet']
    assert _client(hote).get('/api/v1/paiements/profil-versement/').data is None
