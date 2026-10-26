"""Payment required in production, and emails of a booking waiting for payment."""
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.paiements import relances, services
from apps.reservations.models import ReservationModel

FEDAPAY_ACTIF = {'SECRET_KEY': 'sk_sandbox_test', 'ENV': 'sandbox', 'WEBHOOK_SECRET': 'whsec', 'EXPIRATION_MINUTES': 30}


@pytest.fixture(autouse=True)
def pas_de_pause(settings):
    settings.PAIEMENTS_PAUSE_EMAIL = 0


@pytest.fixture
def en_attente(make_hebergement, make_reservation):
    """Booking created just now, to pay within 30 minutes."""
    resa = make_reservation(make_hebergement(name='Villa Lagune', city='Lomé'), status='pending')
    ReservationModel.objects.filter(pk=resa.pk).update(expire_le=timezone.now() + timedelta(minutes=30))
    resa.refresh_from_db()
    return resa


def _decaler(resa, minutes_restantes):
    ReservationModel.objects.filter(pk=resa.pk).update(expire_le=timezone.now() + timedelta(minutes=minutes_restantes))


class TestPaiementObligatoire:
    def test_sans_moyen_de_paiement_la_reservation_est_refusee_en_production(self, settings, client_for, make_user,
                                                                              make_hebergement):
        settings.PAIEMENT_HORS_LIGNE = False
        settings.FEDAPAY = {**FEDAPAY_ACTIF, 'SECRET_KEY': ''}
        settings.PAYPAL = {'CLIENT_ID': '', 'CLIENT_SECRET': '', 'ENV': 'sandbox'}
        logement = make_hebergement()
        debut = timezone.localdate() + timedelta(days=20)
        reponse = client_for(make_user()).post('/api/v1/reservations/', {
            'hebergement': str(logement.id), 'check_in': debut.isoformat(),
            'check_out': (debut + timedelta(days=2)).isoformat(), 'guests_count': 1,
        }, format='json')
        assert reponse.status_code == 503
        assert 'momentanément indisponible' in reponse.data['detail']
        assert not ReservationModel.objects.exists()

    def test_avec_fedapay_la_reservation_attend_le_paiement(self, settings, client_for, make_user, make_hebergement):
        settings.PAIEMENT_HORS_LIGNE, settings.FEDAPAY = False, FEDAPAY_ACTIF
        logement = make_hebergement()
        debut = timezone.localdate() + timedelta(days=20)
        reponse = client_for(make_user()).post('/api/v1/reservations/', {
            'hebergement': str(logement.id), 'check_in': debut.isoformat(),
            'check_out': (debut + timedelta(days=2)).isoformat(), 'guests_count': 1,
        }, format='json')
        assert reponse.status_code == 201
        resa = ReservationModel.objects.get()
        assert resa.status == 'pending' and resa.expire_le

    def test_possible_selon_la_configuration(self, settings):
        settings.FEDAPAY = {**FEDAPAY_ACTIF, 'SECRET_KEY': ''}
        settings.PAYPAL = {'CLIENT_ID': '', 'CLIENT_SECRET': '', 'ENV': 'sandbox'}
        settings.PAIEMENT_HORS_LIGNE = False
        assert services.reservation_possible() is False
        settings.PAIEMENT_HORS_LIGNE = True
        assert services.reservation_possible() is True


class TestRelances:
    def test_email_a_payer_avant_puis_rappel_a_mi_delai(self, en_attente):
        assert relances.envoyer_relances() == 1
        email = mail.outbox[-1]
        assert email.to == [en_attente.guest.email]
        assert email.subject.startswith('Payez avant')
        assert 'Villa Lagune' in email.body and f'/reservation/paiement/{en_attente.id}' in email.body

        # Nothing new while more than half of the delay is left
        assert relances.envoyer_relances() == 0
        _decaler(en_attente, 12)
        assert relances.envoyer_relances() == 1
        assert 'Plus que' in mail.outbox[-1].subject
        assert relances.envoyer_relances() == 0

    def test_annulation_faute_de_paiement_notifiee_une_fois(self, en_attente):
        relances.envoyer_relances()
        _decaler(en_attente, -1)
        assert services.expirer_reservations() == 1
        assert relances.envoyer_relances() == 1
        assert 'annulée' in mail.outbox[-1].subject
        assert 'dates sont de nouveau disponibles' in mail.outbox[-1].body
        assert relances.envoyer_relances() == 0
        assert ReservationModel.objects.get(pk=en_attente.pk).relance_paiement == relances.ANNULATION

    def test_reservation_payee_plus_de_rappel(self, en_attente):
        relances.envoyer_relances()
        ReservationModel.objects.filter(pk=en_attente.pk).update(status='confirmed', expire_le=None)
        _decaler(en_attente, 5)
        assert relances.envoyer_relances() == 0

    def test_annulation_ancienne_sans_email_d_attente_ignoree(self, make_hebergement, make_reservation):
        resa = make_reservation(make_hebergement(), status='cancelled')
        ReservationModel.objects.filter(pk=resa.pk).update(annule_par='expiration')
        assert relances.envoyer_relances() == 0
        assert mail.outbox == []
