"""Payouts that can neither leave twice nor leave by mistake (security audit of 2026-11-07, leads 2, 3 and 5).

FedaPay is simulated: no network call. The simulated FedaPay keeps the status of each payout like the real one,
so a test sees how many payouts were really started, that is how many times money left.
"""
from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.paiements import fedapay, services
from apps.paiements.models import PaiementModel, ProfilVersementModel, RemboursementModel, VersementModel

FEDAPAY_TEST = {'SECRET_KEY': 'sk_sandbox_test', 'ENV': 'sandbox', 'WEBHOOK_SECRET': '', 'EXPIRATION_MINUTES': 30}
PROFIL = '/api/v1/paiements/profil-versement/'
COMPTE = {'pays': 'TG', 'operateur': 'togocel', 'numero': '90000001', 'titulaire': 'Ama Hote'}


class FedaPayEtat:
    """Simulated FedaPay: a payout is "pending" once created, "started" once started."""

    def __init__(self):
        self.payouts = {}
        self.lancement_perdu = 0  # next starts whose answer is lost: the payout is started all the same
        self.lancement_refuse = 0  # next starts refused: the payout stays pending

    def creer_payout(self, *, montant, mode, client):
        identifiant = f'P{len(self.payouts) + 1}'
        self.payouts[identifiant] = {'status': 'pending', 'montant': montant, 'mode': mode,
                                     'numero': client['phone_number']['number']}
        return identifiant

    def lancer_payout(self, identifiant):
        if self.lancement_refuse:
            self.lancement_refuse -= 1
            raise fedapay.FedaPayErreur('Solde insuffisant')
        self.payouts[identifiant]['status'] = 'started'
        if self.lancement_perdu:
            self.lancement_perdu -= 1
            raise fedapay.FedaPayErreur('FedaPay injoignable : ReadTimeout')

    def lire_versement(self, identifiant):
        return {'id': identifiant, 'status': self.payouts[identifiant]['status']}

    def lances(self):
        return [i for i, p in self.payouts.items() if p['status'] != 'pending']


@pytest.fixture
def fedapay_etat(settings, monkeypatch):
    settings.FEDAPAY = FEDAPAY_TEST
    settings.PAIEMENTS_PAUSE_EMAIL = 0
    faux = FedaPayEtat()
    monkeypatch.setattr(fedapay, 'client', mock.Mock(return_value=faux))
    return faux


@pytest.fixture
def versement_du(make_user, make_hebergement, make_reservation):
    """Payout of a confirmed stay, due now, to a host who gave their account."""
    hote = make_user(role='hote')
    resa = make_reservation(make_hebergement(host=hote), starts_in=-2)
    ProfilVersementModel.objects.create(hote_id=hote.pk, **COMPTE)
    return VersementModel.objects.create(reservation_id=resa.id, hote_id=hote.pk, montant_brut=60000, commission=4800,
                                         montant=55200, date_prevue=timezone.now() - timedelta(hours=1))


def _attendre(ligne):
    """Moves the last try back in time, past the waiting delay before a new try."""
    type(ligne).objects.filter(pk=ligne.pk).update(mis_a_jour_le=timezone.now() - timedelta(days=1))


def _hote(client_for, versement):
    return client_for(get_user_model().objects.get(pk=versement.hote_id))


# --- Lead 2: a lost answer must not pay twice ---------------------------------------------------------------------

def test_reponse_perdue_au_lancement_ne_paie_pas_deux_fois(fedapay_etat, versement_du):
    fedapay_etat.lancement_perdu = 1
    services.envoyer_versements_dus()
    _attendre(versement_du)
    services.envoyer_versements_dus()

    assert fedapay_etat.lances() == ['P1']
    versement_du.refresh_from_db()
    assert (versement_du.statut, versement_du.payout_id) == ('en_cours', 'P1')


def test_lancement_refuse_relance_le_meme_payout(fedapay_etat, versement_du):
    fedapay_etat.lancement_refuse = 1
    services.envoyer_versements_dus()
    _attendre(versement_du)
    services.envoyer_versements_dus()

    assert list(fedapay_etat.payouts) == ['P1']
    assert fedapay_etat.lances() == ['P1']


def test_payout_echoue_chez_fedapay_repart_sur_un_nouveau(fedapay_etat, versement_du):
    services.envoyer_versements_dus()
    fedapay_etat.payouts['P1']['status'] = 'failed'
    services.synchroniser_payout(VersementModel.objects.get(pk=versement_du.pk))
    _attendre(versement_du)
    services.envoyer_versements_dus()

    assert fedapay_etat.lances() == ['P1', 'P2']
    versement_du.refresh_from_db()
    assert (versement_du.statut, versement_du.payout_id) == ('en_cours', 'P2')


def test_nouveau_numero_avant_lancement_cree_un_nouveau_payout(fedapay_etat, versement_du):
    fedapay_etat.lancement_refuse = 1
    services.envoyer_versements_dus()
    ProfilVersementModel.objects.filter(hote_id=versement_du.hote_id).update(numero='90000002')
    _attendre(versement_du)
    services.envoyer_versements_dus()

    assert fedapay_etat.lances() == ['P2']
    assert fedapay_etat.payouts['P2']['numero'] == '90000002'


def test_remboursement_reponse_perdue_ne_rembourse_pas_deux_fois(fedapay_etat, make_hebergement, make_reservation):
    resa = make_reservation(make_hebergement(), status='cancelled')
    paiement = PaiementModel.objects.create(reservation_id=resa.id, montant=63600, statut='reussi', transaction_id='T1')
    remboursement = RemboursementModel.objects.create(reservation_id=resa.id, paiement=paiement, montant=63600,
                                                      motif='Annulation', pays='TG', operateur='togocel', numero='90000009')
    fedapay_etat.lancement_perdu = 1
    services.envoyer_remboursements()
    _attendre(remboursement)
    services.envoyer_remboursements()

    assert fedapay_etat.lances() == ['P1']
    remboursement.refresh_from_db()
    assert (remboursement.statut, remboursement.payout_id) == ('en_cours', 'P1')


# --- Lead 5: saving the payout profile again relaunches nothing by itself ------------------------------------------

@pytest.mark.parametrize('compte', [COMPTE, {**COMPTE, 'numero': '90000002'}], ids=['meme_compte', 'nouveau_numero'])
def test_profil_enregistre_ne_relance_pas_un_versement_echoue(fedapay_etat, versement_du, client_for, compte):
    # A failed payout is in the hands of the administrators: they may have paid it by hand
    VersementModel.objects.filter(pk=versement_du.pk).update(
        statut='echoue', tentatives=services.MAX_TENTATIVES, derniere_erreur='Numéro invalide', notifie=True)
    assert _hote(client_for, versement_du).put(PROFIL, compte, format='json').status_code == 200

    versement_du.refresh_from_db()
    assert (versement_du.statut, versement_du.tentatives) == ('echoue', services.MAX_TENTATIVES)
    services.envoyer_versements_dus()
    assert fedapay_etat.payouts == {}


def test_profil_reenregistre_ne_saute_pas_l_attente(fedapay_etat, versement_du, client_for):
    VersementModel.objects.filter(pk=versement_du.pk).update(tentatives=2, derniere_erreur='FedaPay injoignable')
    assert _hote(client_for, versement_du).put(PROFIL, COMPTE, format='json').status_code == 200

    services.envoyer_versements_dus()
    assert fedapay_etat.payouts == {}  # the second try was just now: the next one waits 30 minutes


def test_nouveau_numero_relance_aussitot_un_versement_en_attente(fedapay_etat, versement_du, client_for):
    VersementModel.objects.filter(pk=versement_du.pk).update(tentatives=2, derniere_erreur='Numéro invalide')
    nouveau = {**COMPTE, 'numero': '90000002'}
    assert _hote(client_for, versement_du).put(PROFIL, nouveau, format='json').status_code == 200

    assert services.envoyer_versements_dus() == 1
    assert fedapay_etat.payouts['P1']['numero'] == '90000002'


# --- Lead 3: a closed or banned host is not paid automatically -----------------------------------------------------

def test_versement_d_un_hote_desactive_est_suspendu(fedapay_etat, versement_du):
    comptes = get_user_model().objects.filter(pk=versement_du.hote_id)
    comptes.update(is_active=False)
    assert services.envoyer_versements_dus() == 0
    versement_du.refresh_from_db()
    assert versement_du.statut == 'planifie' and 'désactivé' in versement_du.derniere_erreur
    assert fedapay_etat.payouts == {}

    comptes.update(is_active=True)  # account reactivated by an administrator: the payout leaves
    assert services.envoyer_versements_dus() == 1
