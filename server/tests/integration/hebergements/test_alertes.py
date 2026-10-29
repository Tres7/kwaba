"""The "notify me" alerts of a full listing: creation, double opt-in, triggers, worker, expiry. Emails stay in mail.outbox."""
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.hebergements import alertes
from apps.hebergements.models import AlerteDisponibiliteModel, BlocageModel
from apps.paiements import services as paiements
from apps.reservations.models import ReservationModel
from apps.reservations import paiement as reservations_paiement

HEBERGEMENTS = '/api/v1/hebergements/'


def _jour(n):
    return timezone.localdate() + timedelta(days=n)


@pytest.fixture(autouse=True)
def _sans_pause(settings):
    settings.PAIEMENTS_PAUSE_EMAIL = 0


@pytest.fixture
def complet(make_hebergement, make_user):
    """A one-unit listing booked from day 10 to day 12."""
    h = make_hebergement(name='Villa Soleil')
    r = ReservationModel.objects.create(hebergement_id=h.id, type_logement_id=h.types.get().id, guest=make_user(), check_in=_jour(10),
                                        check_out=_jour(12), total_price=0, status='confirmed')
    return h, r


def _alerte(client, h, debut=10, fin=12, **extra):
    return client.post(f'{HEBERGEMENTS}{h.id}/alertes/', {'debut': _jour(debut).isoformat(), 'fin': _jour(fin).isoformat(), **extra},
                       format='json')


def _passe():
    mail.outbox.clear()
    return alertes.passe()


class TestCreation:
    def test_signed_in_traveller_is_active_at_once(self, client_for, make_user, complet):
        h, _ = complet
        voyageur = make_user()
        reponse = _alerte(client_for(voyageur), h)
        assert reponse.status_code == 201 and reponse.data['statut'] == 'active'
        alerte = AlerteDisponibiliteModel.objects.get()
        assert (alerte.email, alerte.utilisateur, alerte.statut) == (voyageur.email, voyageur, 'active')
        assert _passe() == {'alertes_expirees': 0, 'alertes_confirmations': 0, 'alertes_envoyees': 0}
        assert mail.outbox == []

    def test_dates_still_free(self, client_for, make_user, complet):
        h, _ = complet
        # Departure day of the booking: free for a new arrival
        reponse = _alerte(client_for(make_user()), h, 12, 14)
        assert reponse.status_code == 409 and reponse.data['code'] == 'disponible'
        assert not AlerteDisponibiliteModel.objects.exists()

    def test_partly_taken_dates_are_full(self, client_for, make_user, complet):
        h, _ = complet
        assert _alerte(client_for(make_user()), h, 11, 14).status_code == 201

    @pytest.mark.parametrize('debut, fin', [(-1, 2), (12, 12), (12, 11), (10, 80)])
    def test_invalid_dates(self, client_for, make_user, complet, debut, fin):
        assert _alerte(client_for(make_user()), complet[0], debut, fin).status_code == 400

    def test_without_account_an_email_is_needed(self, complet):
        assert _alerte(APIClient(), complet[0]).status_code == 400

    def test_same_request_twice_keeps_one_alert(self, complet):
        h, _ = complet
        for _ in range(2):
            assert _alerte(APIClient(), h, email='Awa@Exemple.com').status_code == 201
        assert AlerteDisponibiliteModel.objects.get().email == 'awa@exemple.com'

    def test_unpublished_listing(self, client_for, make_user, make_hebergement):
        cache = make_hebergement(is_available=False)
        assert _alerte(client_for(make_user()), cache).status_code == 404

    def test_type_of_another_listing(self, client_for, make_user, complet, make_hebergement):
        autre = make_hebergement().types.get()
        assert _alerte(client_for(make_user()), complet[0], type_logement=str(autre.id)).status_code == 400


class TestDoubleOptIn:
    def test_visitor_confirms_the_address_by_the_emailed_link(self, complet):
        h, _ = complet
        reponse = _alerte(APIClient(), h, email='awa@exemple.com', langue='en')
        assert reponse.data['statut'] == 'a_confirmer'
        alerte = AlerteDisponibiliteModel.objects.get()

        assert _passe()['alertes_confirmations'] == 1
        (email,) = mail.outbox
        assert email.to == ['awa@exemple.com'] and email.subject == 'Confirm your Kwa-Ba alert'
        assert f'/en/alertes?confirmer={alerte.jeton}' in email.body and 'Villa Soleil' in email.body
        assert _passe()['alertes_confirmations'] == 0  # sent once

        confirmation = APIClient().post(f'{HEBERGEMENTS}alertes/confirmer/', {'jeton': alerte.jeton}, format='json')
        assert confirmation.status_code == 200 and confirmation.data['statut'] == 'active'
        alerte.refresh_from_db()
        assert (alerte.statut, alerte.a_verifier) == ('active', True)

    def test_unconfirmed_alert_is_never_sent(self, complet):
        h, reservation = complet
        _alerte(APIClient(), h, email='awa@exemple.com')
        reservations_paiement.annuler(reservation, par='hote')
        assert _passe()['alertes_envoyees'] == 0

    def test_unknown_token(self):
        reponse = APIClient().post(f'{HEBERGEMENTS}alertes/confirmer/', {'jeton': 'inconnu'}, format='json')
        assert reponse.status_code == 404 and reponse.data['detail'] == "Ce lien n'est plus valable."

    def test_signing_in_activates_the_pending_alert(self, client_for, make_user, complet):
        h, _ = complet
        voyageur = make_user(email='awa@exemple.com')
        _alerte(APIClient(), h, email='awa@exemple.com')
        _alerte(client_for(voyageur), h)
        assert AlerteDisponibiliteModel.objects.get().statut == 'active'


class TestTriggers:
    @pytest.fixture
    def active(self, client_for, make_user, complet):
        h, reservation = complet
        _alerte(client_for(make_user(email='awa@exemple.com')), h)
        return h, reservation, AlerteDisponibiliteModel.objects.get()

    def _prevenu(self, alerte):
        assert _passe()['alertes_envoyees'] == 1
        (email,) = mail.outbox
        assert email.to == ['awa@exemple.com'] and 'Villa Soleil' in email.subject
        assert f'check_in={_jour(10)}&check_out={_jour(12)}' in email.body
        alerte.refresh_from_db()
        assert alerte.statut == 'notifiee' and alerte.notifiee_le
        # One email at most per alert
        assert _passe()['alertes_envoyees'] == 0

    def test_cancellation(self, active, django_capture_on_commit_callbacks):
        h, reservation, alerte = active
        with django_capture_on_commit_callbacks(execute=True):
            reservations_paiement.annuler(reservation, par='voyageur')
        self._prevenu(alerte)

    def test_payment_never_made(self, active, make_user, django_capture_on_commit_callbacks):
        h, reservation, alerte = active
        ReservationModel.objects.filter(pk=reservation.pk).update(status='pending', expire_le=timezone.now() - timedelta(minutes=1))
        with django_capture_on_commit_callbacks(execute=True):
            assert reservations_paiement.expirer() == 1
        self._prevenu(alerte)

    def test_closure_reopened(self, client_for, make_user, make_hebergement, django_capture_on_commit_callbacks):
        h = make_hebergement(name='Villa Soleil')
        blocage = BlocageModel.objects.create(hebergement=h, debut=_jour(5), fin=_jour(15))
        _alerte(client_for(make_user(email='awa@exemple.com')), h)
        with django_capture_on_commit_callbacks(execute=True):
            assert client_for(h.host).delete(f'{HEBERGEMENTS}blocages/{blocage.id}/').status_code == 204
        self._prevenu(AlerteDisponibiliteModel.objects.get())

    def test_one_more_unit(self, active, client_for, django_capture_on_commit_callbacks):
        h, _, alerte = active
        with django_capture_on_commit_callbacks(execute=True):
            client_for(h.host).patch(f'{HEBERGEMENTS}types/{h.types.get().id}/', {'quantite': 2}, format='json')
        self._prevenu(alerte)

    def test_other_dates_freed(self, active, make_user, django_capture_on_commit_callbacks):
        h, _, alerte = active
        ailleurs = ReservationModel.objects.create(hebergement_id=h.id, type_logement_id=h.types.get().id, guest=make_user(),
                                                   check_in=_jour(20), check_out=_jour(22), total_price=0, status='confirmed')
        with django_capture_on_commit_callbacks(execute=True):
            reservations_paiement.annuler(ailleurs, par='voyageur')
        alerte.refresh_from_db()
        assert not alerte.a_verifier
        assert _passe()['alertes_envoyees'] == 0

    def test_still_full_after_check(self, active, make_user):
        h, _, alerte = active
        # Flagged, but the dates are still taken (another booking in the meantime): no email, flag cleared
        AlerteDisponibiliteModel.objects.filter(pk=alerte.pk).update(a_verifier=True)
        assert _passe()['alertes_envoyees'] == 0
        alerte.refresh_from_db()
        assert (alerte.statut, alerte.a_verifier) == ('active', False)

    def test_another_type_freed_does_not_satisfy_a_type_alert(self, client_for, make_user, make_hebergement):
        h = make_hebergement(type='hotel', name='Hôtel du Golfe')
        chambre = h.types.get()
        client_for(h.host).post(f'{HEBERGEMENTS}{h.id}/types/', {'nom': 'Suite', 'capacite': 4, 'prix_nuit': 80000, 'quantite': 1},
                                format='json')
        suite = h.types.get(nom='Suite')
        for t in (chambre, suite):
            ReservationModel.objects.create(hebergement_id=h.id, type_logement_id=t.id, guest=make_user(), check_in=_jour(10),
                                            check_out=_jour(12), total_price=0, status='confirmed')
        _alerte(client_for(make_user()), h, type_logement=str(suite.id))
        ReservationModel.objects.filter(type_logement_id=chambre.id).update(status='cancelled')
        AlerteDisponibiliteModel.objects.update(a_verifier=True)
        assert _passe()['alertes_envoyees'] == 0
        # The same freed room satisfies an alert on any type of the hotel
        AlerteDisponibiliteModel.objects.update(type_logement=None, a_verifier=True)
        assert _passe()['alertes_envoyees'] == 1

    def test_listing_hidden_in_the_meantime(self, active):
        h, reservation, alerte = active
        ReservationModel.objects.filter(pk=reservation.pk).update(status='cancelled')
        type(h).objects.filter(pk=h.pk).update(is_available=False)
        AlerteDisponibiliteModel.objects.update(a_verifier=True)
        assert _passe()['alertes_envoyees'] == 0

    def test_worker_pass_runs_the_alerts(self, active, django_capture_on_commit_callbacks):
        h, reservation, alerte = active
        ReservationModel.objects.filter(pk=reservation.pk).update(status='pending', expire_le=timezone.now() - timedelta(minutes=1))
        with django_capture_on_commit_callbacks(execute=True):
            stats = paiements.passe()
        assert stats['reservations_expirees'] == 1
        # In the test transaction the flag is set when the block ends; the worker, in autocommit, sees it at once
        assert _passe()['alertes_envoyees'] == 1


class TestEndOfAlert:
    def test_arrival_date_passed(self, client_for, make_user, complet):
        h, _ = complet
        _alerte(client_for(make_user()), h)
        AlerteDisponibiliteModel.objects.update(date_debut=_jour(-1), date_fin=_jour(1))
        assert _passe()['alertes_expirees'] == 1
        assert AlerteDisponibiliteModel.objects.get().statut == 'expiree'

    def test_arrival_today_is_still_useful(self, client_for, make_user, complet):
        h, _ = complet
        _alerte(client_for(make_user()), h)
        AlerteDisponibiliteModel.objects.update(date_debut=_jour(0))
        assert _passe()['alertes_expirees'] == 0

    def test_address_never_confirmed(self, complet):
        _alerte(APIClient(), complet[0], email='awa@exemple.com')
        AlerteDisponibiliteModel.objects.update(cree_le=timezone.now() - timedelta(days=8))
        assert _passe()['alertes_expirees'] == 1

    def test_unsubscribe(self, client_for, make_user, complet, django_capture_on_commit_callbacks):
        h, reservation = complet
        _alerte(client_for(make_user()), h)
        alerte = AlerteDisponibiliteModel.objects.get()
        reponse = APIClient().post(f'{HEBERGEMENTS}alertes/desinscrire/', {'jeton': alerte.jeton}, format='json')
        assert reponse.status_code == 200 and reponse.data['statut'] == 'annulee'
        with django_capture_on_commit_callbacks(execute=True):
            reservations_paiement.annuler(reservation, par='voyageur')
        assert _passe()['alertes_envoyees'] == 0

    def test_open_alerts_per_address_are_limited(self, client_for, make_user, complet):
        h, _ = complet
        voyageur = make_user()
        AlerteDisponibiliteModel.objects.bulk_create(
            AlerteDisponibiliteModel(hebergement=h, email=voyageur.email, date_debut=_jour(30 + n), date_fin=_jour(31 + n),
                                     statut='active')
            for n in range(alertes.MAX_ALERTES_PAR_EMAIL))
        assert _alerte(client_for(voyageur), h).status_code == 400
