"""Stays in the ledger (FIN-03), through the real payment flow: payment, arrival, cancellation, refund and payout
write their lines in the same transaction as the action. Cases FA-01, FA-02, FA-11, FA-12 and FF-01 to FF-03 of the
test plan; the expected amounts are the booking's frozen ones."""
from datetime import datetime, time, timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.finance import api as finance
from apps.finance.models import MouvementModel
from apps.paiements import api as paiements_api, fedapay, services, tarifs
from apps.paiements.models import (ConditionsHoteModel, PaiementModel, ProfilVersementModel, ReglagesTarifsModel,
                                   RemboursementModel, VersementModel)
from apps.reservations import api as reservations_api
from apps.reservations import paiement as reservations_paiement
from apps.reservations.models import ReservationModel

FEDAPAY_TEST = {'SECRET_KEY': 'sk_sandbox_test', 'ENV': 'sandbox', 'WEBHOOK_SECRET': 'whsec_test',
                'EXPIRATION_MINUTES': 30}


class FauxFedaPay:
    def __init__(self):
        self.statut_transaction = 'pending'
        self.statut_payout = 'started'
        self.compteur = 0

    def creer_transaction(self, **kwargs):
        self.compteur += 1
        return str(1000 + self.compteur), f'https://sandbox-process.fedapay.com/{self.compteur}'

    def lire_transaction(self, identifiant):
        return {'id': identifiant, 'status': self.statut_transaction, 'mode': 'moov_tg',
                'payment_method': {'number': '90000001', 'country': 'tg'}}

    def creer_payout(self, **kwargs):
        self.compteur += 1
        return str(5000 + self.compteur)

    def lancer_payout(self, identifiant):
        pass

    def lire_versement(self, identifiant):
        return {'id': identifiant, 'status': self.statut_payout}


@pytest.fixture(autouse=True)
def faux_fedapay(settings, monkeypatch):
    settings.FEDAPAY, settings.PAIEMENT_HORS_LIGNE, settings.PAIEMENTS_PAUSE_EMAIL = FEDAPAY_TEST, False, 0
    faux = FauxFedaPay()
    monkeypatch.setattr(fedapay, 'client', lambda: faux)
    return faux


@pytest.fixture
def sejour(make_user, make_hebergement, client_for, faux_fedapay):
    hote, voyageur = make_user(role='hote'), make_user()
    logement = make_hebergement(host=hote, price_per_night=20_000)
    api = client_for(voyageur)

    def reserver(dans_jours=30, nuits=3) -> ReservationModel:
        debut = timezone.localdate() + timedelta(days=dans_jours)
        r = api.post('/api/v1/reservations/', {'hebergement': str(logement.id), 'check_in': debut.isoformat(),
                                               'check_out': (debut + timedelta(days=nuits)).isoformat(),
                                               'guests_count': 2}, format='json')
        assert r.status_code == 201, r.content
        return ReservationModel.objects.get(pk=r.data['id'])

    def payer(reservation) -> PaiementModel:
        assert api.post(f'/api/v1/paiements/reservations/{reservation.id}/payer/').status_code == 200
        faux_fedapay.statut_transaction = 'approved'
        api.get(f'/api/v1/paiements/reservations/{reservation.id}/statut/')
        reservation.refresh_from_db()
        return PaiementModel.objects.get(reservation_id=reservation.id, statut='reussi')

    return SimpleNamespace(hote=hote, voyageur=voyageur, api=api, reserver=reserver, payer=payer, faux=faux_fedapay)


def lignes(reservation) -> dict[tuple[str, str], int]:
    """(nature, direction) -> amount, the lines of a booking (corrections included, with their direction)."""
    total: dict[tuple[str, str], int] = {}
    for m in MouvementModel.objects.filter(reservation_id=reservation.id):
        total[(m.nature_id, m.sens)] = total.get((m.nature_id, m.sens), 0) + m.montant
    return total


def du_hote(sejour) -> int:
    return {r['tiers_id']: r['solde_du'] for r in finance.du_aux_partenaires()}.get(str(sejour.hote.pk), 0)


def revenu() -> int:
    aujourdhui = timezone.now().date()
    return sum(r['montant'] for r in finance.synthese(aujourdhui - timedelta(days=60), aujourdhui + timedelta(days=60),
                                                      'nature', familles=['R']))


def arrivee_passee(reservation) -> int:
    moment = timezone.make_aware(datetime.combine(reservation.check_in, time(15, 0)))
    return reservations_paiement.constater_commissions(maintenant=moment)


def test_a_paid_stay_writes_nights_and_cleaning_for_the_host_and_fees_for_kwaba(sejour):
    """FA-01, FA-12: the split of the frozen amounts, under the provider's reference, the cleaning never in revenue."""
    r = sejour.reserver()
    paiement = sejour.payer(r)

    attendu = {('T01', 'entree'): r.prix_nuits, ('R01', 'entree'): r.frais_service}
    if r.frais_menage:
        attendu[('T02', 'entree')] = r.frais_menage
    assert lignes(r) == attendu
    t01 = MouvementModel.objects.get(reservation_id=r.id, nature_id='T01')
    assert (t01.offre_id, t01.tiers_type_id, t01.tiers_id, t01.moyen_paiement_id, t01.externe_reference,
            t01.piece_reference) == ('COURTE_DUREE', 'hote', str(sejour.hote.pk), 'MOOV', paiement.transaction_id,
                                     r.reference)
    # I2: total paid = owed to the host + Kwa-Ba's revenue
    assert r.total_price == paiement.montant == du_hote(sejour) + revenu()
    assert all(i['anomalies'] == 0 for i in finance.controle_invariants())


def test_the_status_checked_twice_writes_the_payment_once(sejour):
    """FB-04 through the flow: the browser and the webhook can both confirm the payment."""
    r = sejour.reserver()
    sejour.payer(r)
    services.synchroniser_paiement(PaiementModel.objects.get(reservation_id=r.id))

    assert MouvementModel.objects.filter(reservation_id=r.id, nature_id='T01').count() == 1


def test_the_commission_becomes_revenue_at_the_arrival_once(sejour):
    """FA-01: at the arrival, the commission moves from the host's money to Kwa-Ba's revenue."""
    r = sejour.reserver(dans_jours=1)
    sejour.payer(r)

    assert arrivee_passee(r) == 1
    assert arrivee_passee(r) == 0

    r.refresh_from_db()
    assert r.commission_constatee_le is not None
    assert lignes(r)[('R02', 'entree')] == lignes(r)[('T01', 'sortie')] == r.commission_hote
    assert du_hote(sejour) == r.prix_nuits - r.commission_hote + (r.frais_menage or 0) == r.montant_hote
    assert revenu() == r.frais_service + r.commission_hote


def test_a_stay_not_paid_online_is_only_marked(sejour, make_hebergement, make_reservation):
    r = make_reservation(make_hebergement(), starts_in=0)

    arrivee_passee(r)

    r.refresh_from_db()
    assert r.commission_constatee_le is not None and lignes(r) == {}


def test_a_hotel_writes_its_offer_and_its_commission(sejour):
    """FA-02: hotel or residence: offer HOTEL, commission R03."""
    ConditionsHoteModel.objects.create(hote_id=sejour.hote.pk, categorie='hotel')
    r = sejour.reserver(dans_jours=1)
    sejour.payer(r)
    arrivee_passee(r)

    t01 = MouvementModel.objects.filter(reservation_id=r.id, nature_id='T01').first()
    assert (t01.offre_id, t01.tiers_type_id) == ('HOTEL', 'hotel')
    assert lignes(r)[('R03', 'entree')] == r.commission_hote == tarifs.arrondi(r.prix_nuits * tarifs.COMMISSION_HOTEL)


def test_a_free_cancellation_gives_everything_back_and_leaves_no_revenue(sejour):
    """FF-01: refunded in full, the fees with it; the money is owed to the traveller, then leaves with the refund."""
    r = sejour.reserver(dans_jours=30)
    paiement = sejour.payer(r)

    rembourse = reservations_api.annuler(r, 'voyageur')

    assert rembourse == paiement.montant
    assert revenu() == 0 and du_hote(sejour) == 0
    assert lignes(r)[('T05', 'entree')] == paiement.montant
    remboursement = RemboursementModel.objects.get(reservation_id=r.id)
    assert remboursement.statut == 'a_envoyer'

    services.envoyer_remboursements()
    sejour.faux.statut_payout = 'sent'
    services.synchroniser_remboursement(RemboursementModel.objects.get(pk=remboursement.pk))

    assert lignes(r)[('T05', 'sortie')] == paiement.montant
    assert finance.soldes_comptes_argent() == {'FEDAPAY': 0}
    assert all(i['anomalies'] == 0 for i in finance.controle_invariants())


def test_a_late_cancellation_keeps_kwabas_share_in_r08(sejour):
    """FF-02: the kept nights go to the host minus Kwa-Ba's share, written as R08; the fees stay Kwa-Ba's."""
    r = sejour.reserver(dans_jours=2)
    paiement = sejour.payer(r)
    bareme = tarifs.bareme_voyageur(tarifs.montants_de(r), r)
    assert bareme.nuits_retenues > 0, 'a late cancellation keeps nights'

    reservations_api.annuler(r, 'voyageur')

    assert lignes(r).get(('R08', 'entree')) == bareme.commission_hote
    assert du_hote(sejour) == bareme.montant_hote
    assert revenu() == r.frais_service + bareme.commission_hote
    assert lignes(r)[('T05', 'entree')] == bareme.rembourse_voyageur
    # Nothing left unclassified: owed to the host + Kwa-Ba's revenue + owed to the traveller = what was paid
    assert du_hote(sejour) + revenu() + bareme.rembourse_voyageur == paiement.montant


def test_a_cancellation_after_the_arrival_takes_back_the_commission_first(sejour):
    r = sejour.reserver(dans_jours=1)
    paiement = sejour.payer(r)
    arrivee_passee(r)
    r.refresh_from_db()

    reservations_api.annuler(r, 'hote')

    assert revenu() == 0 and du_hote(sejour) == 0
    assert lignes(r)[('T05', 'entree')] == paiement.montant
    assert finance.soldes_comptes_argent() == {'FEDAPAY': paiement.montant}


def test_a_payment_after_the_cancellation_is_owed_back_at_once(sejour):
    """A payment confirmed after the booking was cancelled: nothing for the host, everything owed to the traveller."""
    r = sejour.reserver()
    assert sejour.api.post(f'/api/v1/paiements/reservations/{r.id}/payer/').status_code == 200
    ReservationModel.objects.filter(pk=r.pk).update(status='cancelled', annule_par='voyageur')
    sejour.faux.statut_transaction = 'approved'
    sejour.api.get(f'/api/v1/paiements/reservations/{r.id}/statut/')

    paiement = PaiementModel.objects.get(reservation_id=r.id)
    assert paiement.statut == 'reussi'
    assert lignes(r) == {('T05', 'entree'): paiement.montant}
    assert finance.du_aux_partenaires() == [{'tiers_type': 'voyageur', 'tiers_id': str(sejour.voyageur.pk),
                                             'solde_du': paiement.montant}]


def test_the_payout_to_the_host_settles_what_is_owed(sejour):
    """FH-11 through the flow: once the payout is sent, Kwa-Ba owes the host nothing."""
    ProfilVersementModel.objects.create(hote_id=sejour.hote.pk, pays='TG', operateur='moov_tg', numero='90000002',
                                        titulaire='Ama Hote')
    r = sejour.reserver(dans_jours=1)
    sejour.payer(r)
    arrivee_passee(r)
    VersementModel.objects.filter(reservation_id=r.id).update(date_prevue=timezone.now() - timedelta(minutes=1))

    services.envoyer_versements_dus()
    sejour.faux.statut_payout = 'sent'
    versement = VersementModel.objects.get(reservation_id=r.id)
    services.synchroniser_payout(versement)

    assert VersementModel.objects.get(pk=versement.pk).statut == 'envoye'
    assert lignes(r)[('T09', 'sortie')] == r.montant_hote
    assert du_hote(sejour) == 0
    assert finance.soldes_comptes_argent() == {'FEDAPAY': r.frais_service + r.commission_hote}


def test_fees_lowered_after_the_payment_are_rectified_and_owed_back(sejour):
    """Stay Pack + Driver: R01 is brought to the reduced fees, the difference is owed to the traveller."""
    r = sejour.reserver()
    sejour.payer(r)
    frais_avant = r.frais_service

    ecart, _ = reservations_api.reduire_frais_pack_sejour(r.id, sejour.voyageur.pk)
    paiements_api.rembourser_en_partie('reservation', r.id, ecart, 'Pack Séjour')

    r.refresh_from_db()
    assert revenu() == r.frais_service == frais_avant - ecart
    assert lignes(r)[('T05', 'entree')] == ecart


def test_a_rate_changed_after_the_payment_changes_nothing_written(sejour):
    """FA-11: the lines keep the amounts frozen at the booking."""
    r = sejour.reserver()
    sejour.payer(r)
    avant = lignes(r)

    ReglagesTarifsModel.objects.update_or_create(pk=1, defaults={'frais_voyageur': '0.07'})
    tarifs.oublier()

    assert lignes(r) == avant


def test_money_older_than_the_ledger_is_never_written_afterwards(sejour):
    """A stay paid before the ledger existed, then cancelled: no exit is written for what never came in."""
    autre = sejour.reserver(dans_jours=40)
    PaiementModel.objects.create(reservation_id=autre.id, montant=autre.total_price, statut='reussi',
                                 transaction_id='ANCIEN-1', mode='moov_tg')
    ReservationModel.objects.filter(pk=autre.pk).update(status='confirmed')
    autre.refresh_from_db()

    reservations_api.annuler(autre, 'voyageur')

    assert lignes(autre) == {}
    assert RemboursementModel.objects.filter(reservation_id=autre.id).exists()
