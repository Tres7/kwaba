"""Payment of a stay by a third party: secret link, payer's page, refunds to the payer, Together.

FedaPay is simulated: no network call, no real email (Django's test outbox)."""
from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

from apps.paiements import fedapay, notifications, services
from apps.paiements.models import PaiementModel, RemboursementModel
from apps.reservations import paiement as reservations_paiement
from apps.reservations.models import DemandePaiementModel, ReservationModel

RESERVATIONS = '/api/v1/reservations/'
PAIEMENTS = '/api/v1/paiements/'
VOYAGES = '/api/v1/voyages/'
FEDAPAY_TEST = {'SECRET_KEY': 'sk_sandbox_test', 'ENV': 'sandbox', 'WEBHOOK_SECRET': '', 'EXPIRATION_MINUTES': 30}


class Faux:
    """Simulated FedaPay: collection and payouts (refunds)."""

    def __init__(self):
        self.transaction = 'pending'
        self.telephone = '90000009'
        self.clients = []
        self.payouts = []

    def creer_transaction(self, **kwargs):
        self.clients.append(kwargs['client'])
        return str(700 + len(self.clients)), f'https://sandbox-process.fedapay.com/{len(self.clients)}'

    def lire_transaction(self, identifiant):
        client = {'phone_number': {'number': self.telephone, 'country': 'tg'}} if self.telephone else {}
        return {'id': identifiant, 'status': self.transaction, 'mode': 'momo_test', 'customer': client}

    def creer_payout(self, **kwargs):
        self.payouts.append(kwargs)
        return f'P{len(self.payouts)}'

    def lancer_payout(self, identifiant):
        pass

    def lire_versement(self, identifiant):
        return {'id': identifiant, 'status': 'started'}


@pytest.fixture
def faux(settings, monkeypatch):
    settings.FEDAPAY = FEDAPAY_TEST
    settings.PAIEMENT_HORS_LIGNE = False
    settings.PAIEMENTS_PAUSE_EMAIL = 0
    f = Faux()
    monkeypatch.setattr(fedapay, 'client', mock.Mock(return_value=f))
    return f


@pytest.fixture
def sejour(faux, client_for, make_user, make_hebergement):
    """A pending booking of Ama, who asks Kofi to pay it."""
    voyageur = make_user(first_name='Ama', last_name='Mensah')
    annonce = make_hebergement(name='Villa Bè', city='Lomé', location='Rue 12, Bè Kpota', price_per_night=25000)
    debut = timezone.localdate() + timedelta(days=10)
    r = client_for(voyageur).post(RESERVATIONS, {
        'hebergement': str(annonce.id), 'check_in': debut.isoformat(),
        'check_out': (debut + timedelta(days=2)).isoformat(), 'guests_count': 2,
    }, format='json')
    assert r.status_code == 201, r.data
    return {'voyageur': voyageur, 'annonce': annonce, 'reservation': ReservationModel.objects.get(pk=r.data['id']),
            'payeur': make_user(first_name='Kofi', last_name='Adjei')}


def _lien(client_for, s) -> str:
    r = client_for(s['voyageur']).post(f"{PAIEMENTS}reservations/{s['reservation'].id}/demande-tiers/")
    assert r.status_code == 201, r.data
    return r.data['lien'].rsplit('/', 1)[1]


def _payer(client_for, payeur, jeton, faux):
    r = client_for(payeur).post(f'{PAIEMENTS}tiers/{jeton}/', {'moyen': 'mobile_money'}, format='json')
    assert r.status_code == 200, r.data
    faux.transaction = 'approved'
    demande = DemandePaiementModel.objects.get()
    return client_for(payeur).get(f'{PAIEMENTS}tiers/demandes/{demande.id}/statut/')


def test_le_tiers_paie_le_sejour_et_recoit_son_recu(client_for, sejour, faux):
    jeton = _lien(client_for, sejour)
    payeur = sejour['payeur']

    apercu = client_for(payeur).get(f'{PAIEMENTS}tiers/{jeton}/').data
    assert apercu['payable'] and apercu['voyageur'] == 'Ama'
    assert (apercu['hebergement']['name'], apercu['hebergement']['city']) == ('Villa Bè', 'Lomé')
    assert apercu['total'] == sejour['reservation'].total_price
    # Neither the address nor anyone's contact details
    assert 'Bè Kpota' not in str(apercu) and sejour['voyageur'].email not in str(apercu)

    statut = _payer(client_for, payeur, jeton, faux).data
    assert statut == {'reservation': 'confirmed', 'paiement': 'reussi', 'voyageur': 'Ama'}
    assert faux.clients[0]['email'] == payeur.email  # FedaPay sees the payer, not the traveller
    assert PaiementModel.objects.get().payeur_id == payeur.pk

    mail.outbox.clear()
    notifications.envoyer_notifications()
    au_payeur = next(m for m in mail.outbox if m.to == [payeur.email])
    assert 'séjour de Ama' in au_payeur.subject
    assert [a[0] for a in au_payeur.attachments if isinstance(a, tuple)] == [f"recu-{sejour['reservation'].reference}.pdf"]
    assert 'Bè Kpota' not in au_payeur.body
    au_voyageur = next(m for m in mail.outbox if m.to == [sejour['voyageur'].email])
    assert 'Kofi A. a payé votre séjour' in au_voyageur.body


def test_le_remboursement_revient_au_payeur(client_for, sejour, faux):
    jeton = _lien(client_for, sejour)
    _payer(client_for, sejour['payeur'], jeton, faux)
    assert client_for(sejour['voyageur']).delete(f"{RESERVATIONS}{sejour['reservation'].id}/").status_code == 200

    remboursement = RemboursementModel.objects.get()
    assert remboursement.payeur.pk == sejour['payeur'].pk
    services.envoyer_remboursements()
    assert faux.payouts[0]['client']['phone_number']['number'] == '90000009'  # the number charged
    assert faux.payouts[0]['client']['email'] == sejour['payeur'].email


def test_le_voyageur_ne_detourne_pas_le_remboursement_du_payeur(client_for, sejour, faux):
    faux.telephone = ''  # FedaPay did not give the number charged
    jeton = _lien(client_for, sejour)
    _payer(client_for, sejour['payeur'], jeton, faux)
    client_for(sejour['voyageur']).delete(f"{RESERVATIONS}{sejour['reservation'].id}/")

    remboursement = RemboursementModel.objects.get()
    assert remboursement.statut == 'a_traiter'  # the administrators ask the payer
    compte = {'pays': 'TG', 'operateur': 'togocel', 'numero': '90000001'}
    r = client_for(sejour['voyageur']).put(f"{PAIEMENTS}reservations/{sejour['reservation'].id}/compte-remboursement/",
                                           compte, format='json')
    assert r.status_code == 400
    assert RemboursementModel.objects.get().numero == ''


def test_qui_ne_peut_pas_payer(client_for, api_client, sejour, faux, make_user):
    jeton = _lien(client_for, sejour)
    url = f'{PAIEMENTS}tiers/{jeton}/'
    assert api_client.get(url).status_code == 401  # an account is needed
    assert 'votre réservation' in client_for(sejour['voyageur']).post(url, {}, format='json').data['detail']
    hote = get_user_model().objects.get(pk=sejour['annonce'].host_id)
    assert "L'hôte" in client_for(hote).post(url, {}, format='json').data['detail']
    assert client_for(sejour['payeur']).get(f'{PAIEMENTS}tiers/inconnu/').status_code == 404
    assert not faux.clients


def test_un_nouveau_lien_ou_sa_desactivation_ferment_l_ancien(client_for, sejour, faux):
    ancien = _lien(client_for, sejour)
    nouveau = _lien(client_for, sejour)
    payeur = client_for(sejour['payeur'])
    assert payeur.get(f'{PAIEMENTS}tiers/{ancien}/').data['payable'] is False
    assert payeur.get(f'{PAIEMENTS}tiers/{nouveau}/').data['payable'] is True

    client_for(sejour['voyageur']).delete(f"{PAIEMENTS}reservations/{sejour['reservation'].id}/demande-tiers/")
    assert payeur.post(f'{PAIEMENTS}tiers/{nouveau}/', {}, format='json').status_code == 400


def test_le_lien_expire_apres_24_heures(client_for, sejour, faux):
    jeton = _lien(client_for, sejour)
    DemandePaiementModel.objects.update(expire_le=timezone.now() - timedelta(minutes=1))
    r = client_for(sejour['payeur']).post(f'{PAIEMENTS}tiers/{jeton}/', {}, format='json')
    assert r.status_code == 400 and "n'est plus valable" in r.data['detail']


def test_apres_le_blocage_des_dates_le_tiers_paie_si_elles_sont_libres(client_for, sejour, faux):
    jeton = _lien(client_for, sejour)
    # Expiry email: the link still works
    assert reservations_paiement._decrire_relance(sejour['reservation'])['lien_tiers']
    ReservationModel.objects.update(expire_le=timezone.now() - timedelta(minutes=1))
    assert reservations_paiement.expirer() == 1  # the dates are released after 30 minutes

    assert _payer(client_for, sejour['payeur'], jeton, faux).data['reservation'] == 'confirmed'


def test_apres_le_blocage_des_dates_prises_par_un_autre_le_paiement_est_refuse(client_for, sejour, faux, make_user):
    jeton = _lien(client_for, sejour)
    ReservationModel.objects.update(expire_le=timezone.now() - timedelta(minutes=1))
    reservations_paiement.expirer()
    r = sejour['reservation']
    ReservationModel.objects.create(hebergement_id=r.hebergement_id, type_logement_id=r.type_logement_id,
                                    guest_id=make_user().pk, check_in=r.check_in, check_out=r.check_out,
                                    total_price=0, status='confirmed')

    reponse = client_for(sejour['payeur']).post(f'{PAIEMENTS}tiers/{jeton}/', {}, format='json')
    assert reponse.status_code == 400 and 'plus disponibles' in reponse.data['detail']
    assert not faux.clients


# --- Together: a member pays the booking of the group ------------------------------------------------------------

def test_un_membre_paie_la_reservation_du_groupe(client_for, sejour, faux, make_user):
    orga = client_for(sejour['voyageur'])
    debut = timezone.localdate() + timedelta(days=30)
    voyage = orga.post(VOYAGES, {'nom': 'Lomé entre amis', 'destination': 'Lomé', 'date_debut': debut.isoformat(),
                                 'date_fin': (debut + timedelta(days=3)).isoformat(), 'nb_voyageurs': 2},
                       format='json').data
    membre = client_for(sejour['payeur'])
    assert membre.post(f"{VOYAGES}invitations/{voyage['code_invitation']}/").status_code == 200
    detail = orga.post(f"{VOYAGES}{voyage['id']}/reservations/", {'reservation': str(sejour['reservation'].id)},
                       format='json').data
    lien = detail['reservations'][0]
    assert lien['peut_demander_paiement'] and not lien['paiement_groupe']
    url = f"{VOYAGES}{voyage['id']}/reservations/{lien['id']}/"

    assert membre.post(f'{url}demande-paiement/').status_code == 400  # only the booker asks
    assert orga.post(f'{url}demande-paiement/').data['reservations'][0]['paiement_groupe'] is True
    assert membre.get(f'{url}paiement/').data['voyageur'] == 'Ama'
    assert client_for(make_user()).get(f'{url}paiement/').status_code == 404  # not a member

    assert membre.post(f'{url}paiement/', {'moyen': 'mobile_money'}, format='json').status_code == 200
    faux.transaction = 'approved'
    statut = membre.get(f"{PAIEMENTS}tiers/demandes/{DemandePaiementModel.objects.get().id}/statut/").data
    assert statut['reservation'] == 'confirmed'
    assert PaiementModel.objects.get(statut='reussi').payeur_id == sejour['payeur'].pk


def test_l_organisateur_ne_demande_plus_au_groupe(client_for, sejour, faux):
    orga = client_for(sejour['voyageur'])
    voyage = orga.post(VOYAGES, {'nom': 'Week-end', 'destination': 'Lomé', 'nb_voyageurs': 2}, format='json').data
    membre = client_for(sejour['payeur'])
    membre.post(f"{VOYAGES}invitations/{voyage['code_invitation']}/")
    lien = orga.post(f"{VOYAGES}{voyage['id']}/reservations/", {'reservation': str(sejour['reservation'].id)},
                     format='json').data['reservations'][0]
    url = f"{VOYAGES}{voyage['id']}/reservations/{lien['id']}/"
    orga.post(f'{url}demande-paiement/')
    assert orga.delete(f'{url}demande-paiement/').data['reservations'][0]['paiement_groupe'] is False
    assert membre.get(f'{url}paiement/').status_code == 404
