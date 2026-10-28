import re
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.hebergements.models import HebergementModel
from apps.hebergements.types_logement import assurer_type_par_defaut
from apps.reservations.models import ReservationModel
from apps.users.infrastructure.messaging.RabbitMQEventBus import RabbitMQEventBus
from apps.users.infrastructure.persistence.models import UserModel

PASSWORD = 'Kwaba-Test-2026!'


@pytest.fixture(autouse=True)
def _db_and_fast_hasher(db, settings):
    # All integration tests have access to the database; a fast hasher saves ~0.3 s per password
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@pytest.fixture(autouse=True)
def _paiement_hors_ligne(settings):
    # Without FedaPay configured, tests book without payment (like in development); see test_paiement_obligatoire
    settings.PAIEMENT_HORS_LIGNE = True


@pytest.fixture(autouse=True)
def _site_ouvert(settings):
    # Site open by default, whatever a local server/.env says; pre-launch tests turn it on themselves
    settings.PRELANCEMENT = False


@pytest.fixture(autouse=True)
def _broker_down(monkeypatch):
    """Without RabbitMQ, FallbackEventBus sends the email directly (mail.outbox).

    Real exchanges with the broker are tested in tests/broker.
    """
    def refuse_connection(self, event):
        raise ConnectionError('RabbitMQ indisponible (tests d\'intégration)')

    monkeypatch.setattr(RabbitMQEventBus, 'publish', refuse_connection)


@pytest.fixture
def password():
    return PASSWORD


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user():
    counter = iter(range(1, 10_000))

    def _make(role='voyageur', is_verified=True, **fields):
        n = next(counter)
        fields.setdefault('email', f'{role}{n}@test.kwaba')
        fields.setdefault('first_name', 'Test')
        fields.setdefault('last_name', f'{role.capitalize()} {n}')
        if role == 'hote':
            # Phone required to publish a listing (the agent calls the host for the visit)
            fields.setdefault('phone', f'+22991{n:06d}')
        return UserModel.objects.create_user(password=PASSWORD, role=role, is_verified=is_verified, **fields)

    return _make


@pytest.fixture
def code_envoye():
    """Last 6-digit code emailed to this address (the database only keeps its fingerprint)."""
    def _lire(email):
        for message in reversed(mail.outbox):
            if email.lower() in [d.lower() for d in message.to]:
                trouve = re.search(r'\b(\d{6})\b', message.body)
                if trouve:
                    return trouve.group(1)
        raise AssertionError(f'Aucun code envoyé à {email}')

    return _lire


@pytest.fixture
def make_hebergement(make_user):
    def _make(host=None, **fields):
        fields.setdefault('name', 'Villa test')
        fields.setdefault('city', 'Lomé')
        fields.setdefault('price_per_night', 25000)
        # Listing already verified by an agent (published); the verification tests pass statut_verification
        fields.setdefault('statut_verification', 'verifiee')
        hebergement = HebergementModel.objects.create(host=host or make_user(role='hote'), **fields)
        # Like every establishment in production: one default unit type (quantity 1)
        assurer_type_par_defaut(hebergement)
        return hebergement

    return _make


@pytest.fixture
def raw_client():
    """Client that returns the 500 response instead of raising the view's exception ("never 500" tests)."""
    client = APIClient()
    client.raise_request_exception = False
    return client


@pytest.fixture
def client_for():
    """A separate authenticated client per user."""
    def _login_as(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _login_as


@pytest.fixture
def make_reservation(make_user):
    """Booking written directly in the database (including in the past, impossible through the API)."""
    def _make(hebergement, guest=None, starts_in=10, nights=3, status='confirmed'):
        check_in = timezone.localdate() + timedelta(days=starts_in)
        return ReservationModel.objects.create(
            hebergement=hebergement, guest=guest or make_user(), check_in=check_in,
            check_out=check_in + timedelta(days=nights), total_price=0, status=status,
        )

    return _make
