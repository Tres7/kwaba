"""Opening: the host agreement once the company is registered (RCCM and NIF), invitations and publication rule."""
import uuid
from datetime import timedelta

import pytest
from django.core import mail
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.contrats import preinscription
from apps.contrats.models import ContratModel, PreinscriptionModel
from apps.documents.models import ParametresSocieteModel
from apps.hebergements.models import HebergementModel

HEBERGEMENTS = '/api/v1/hebergements/'
SOCIETE = '/api/v1/admin/documents/societe/'


@pytest.fixture
def societe():
    """Company name and address only: enough for invoices, not yet registered."""
    return ParametresSocieteModel.objects.update_or_create(pk=1, defaults={
        'raison_sociale': 'Kwaba SAS', 'forme_juridique': 'SAS', 'adresse': 'Boulevard du 13 Janvier, Lomé'})[0]


@pytest.fixture
def immatriculee(societe):
    societe.rccm, societe.nif = 'TG-LOM-2026-B-1', '1000123456'
    societe.save()
    return societe


def _contrat_signe(hote):
    return ContratModel.objects.create(
        reference=f'CT-T-{uuid.uuid4().hex[:6]}', type='hote', titre='Contrat hôte', corps='Texte', version_modele=1,
        statut='signe', hote_id=hote.pk, partie_nom=hote.get_full_name(), partie_email=hote.email, kwaba_signataire='Kwaba SAS',
        jeton_hash=uuid.uuid4().hex, expire_le=timezone.now() + timedelta(days=30), signe_le=timezone.now(),
    )


def _preinscrire(hote, langue='fr'):
    return PreinscriptionModel.objects.create(hote_id=hote.pk, version=preinscription.VERSION, langue=langue,
                                              empreinte_texte=preinscription.empreinte(langue))


def test_agreement_is_not_offered_before_registration(client_for, make_user, societe):
    assert client_for(make_user(role='hote')).get('/api/v1/contrats/hote/').status_code == 404


def test_before_registration_a_verified_listing_needs_no_agreement(api_client, make_hebergement, societe):
    hebergement = make_hebergement()
    assert api_client.get(HEBERGEMENTS).data['count'] == 1
    assert api_client.get(f'{HEBERGEMENTS}{hebergement.id}/').status_code == 200


def test_after_registration_only_listings_of_signed_hosts_are_public(api_client, client_for, make_user, make_hebergement, immatriculee):
    sans_contrat = make_hebergement(name='Hôte sans contrat')
    avec_contrat = make_hebergement(name='Hôte avec contrat')
    _contrat_signe(avec_contrat.host)

    assert [h['name'] for h in api_client.get(HEBERGEMENTS).data['results']] == ['Hôte avec contrat']
    assert api_client.get(f'{HEBERGEMENTS}{sans_contrat.id}/').status_code == 404
    # The host still sees their listing and can sign from their space
    assert client_for(sans_contrat.host).get(f'{HEBERGEMENTS}{sans_contrat.id}/').status_code == 200
    assert client_for(sans_contrat.host).get('/api/v1/contrats/hote/').status_code == 200
    # ...and is told the listing is not online yet, unlike the host who signed
    assert client_for(sans_contrat.host).get(f'{HEBERGEMENTS}mine/').data['results'][0]['en_ligne'] is False
    assert client_for(avec_contrat.host).get(f'{HEBERGEMENTS}mine/').data['results'][0]['en_ligne'] is True
    assert 'en_ligne' in api_client.get(HEBERGEMENTS).data['results'][0]  # null for the public


def test_registration_invites_each_host_to_sign_once(client_for, make_user, make_hebergement, societe,
                                                     django_capture_on_commit_callbacks):
    admin = client_for(make_user(role='admin'))
    preinscrit_en = make_user(role='hote', first_name='Kofi')
    _preinscrire(preinscrit_en, langue='en')
    avec_annonce = make_hebergement().host
    deja_signe = make_user(role='hote')
    _preinscrire(deja_signe)
    _contrat_signe(deja_signe)
    make_user(role='hote')            # neither pre-registered nor any listing
    make_user()                       # traveller
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        assert admin.put(SOCIETE, {'rccm': 'TG-LOM-2026-B-1'}, format='json').status_code == 200
    assert mail.outbox == []          # NIF still missing: not registered yet

    with django_capture_on_commit_callbacks(execute=True):
        assert admin.put(SOCIETE, {'nif': '1000123456'}, format='json').status_code == 200
    assert sorted(m.to[0] for m in mail.outbox) == sorted([preinscrit_en.email, avec_annonce.email])
    anglais = next(m for m in mail.outbox if m.to == [preinscrit_en.email])
    assert anglais.subject == 'Your Kwa-Ba host agreement is ready to sign'
    assert 'Hello Kofi' in anglais.body and '/en/hote/espace/contrat' in anglais.body
    francais = next(m for m in mail.outbox if m.to == [avec_annonce.email])
    assert 'Kwaba SAS est maintenant immatriculée' in francais.body and '/hote/espace/contrat' in francais.body

    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        admin.put(SOCIETE, {'email': 'contact@kwa-ba.com'}, format='json')
    assert mail.outbox == []          # already registered: no second invitation


def test_reminder_command(make_hebergement, societe):
    make_hebergement()
    with pytest.raises(CommandError):
        call_command('inviter_hotes_contrat')

    societe.rccm, societe.nif = 'TG-LOM-2026-B-1', '1000123456'
    societe.save()
    mail.outbox.clear()
    call_command('inviter_hotes_contrat')
    assert len(mail.outbox) == 1


def test_building_the_public_queryset_runs_no_query(django_assert_num_queries):
    # Serializer fields build it at import time, before the tables exist (manage.py check, migrate on a new database)
    with django_assert_num_queries(0):
        HebergementModel.objects.publiees()


def test_favourites_follow_a_registration_made_while_the_api_runs(client_for, make_user, make_hebergement, societe):
    hebergement = make_hebergement()
    client = client_for(make_user())
    societe.rccm, societe.nif = 'TG-LOM-2026-B-1', '1000123456'
    societe.save()

    # The favourites serializer was built before the registration: its listing rule must still apply now
    assert client.post('/api/v1/favoris/', {'hebergement': str(hebergement.id)}, format='json').status_code == 400
    _contrat_signe(hebergement.host)
    assert client.post('/api/v1/favoris/', {'hebergement': str(hebergement.id)}, format='json').status_code == 201
