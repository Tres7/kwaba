"""Kwa-Ba Give: donation, payment, monthly transfer to NGOs, emails, public API and admin."""
from datetime import date, datetime, timedelta
from unittest import mock

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

from apps.give import services
from apps.give.models import DonModel, OrganisationModel, ProjetModel, ReversementModel
from apps.paiements import fedapay, paypal
from apps.paiements import services as paiements
from apps.paiements.models import PaiementModel

GIVE = '/api/v1/give/'


class Faux:
    """Simulated FedaPay."""

    def __init__(self):
        self.statut = 'approved'
        self.erreur = False
        self.dernier = {}

    def creer_transaction(self, **kwargs):
        if self.erreur:
            raise fedapay.FedaPayErreur('panne')
        self.dernier = kwargs
        return f'T{DonModel.objects.count()}', 'https://sandbox-process.fedapay.com/t'

    def lire_transaction(self, identifiant):
        return {'id': identifiant, 'status': self.statut, 'mode': 'momo_test'}


@pytest.fixture
def faux(settings, monkeypatch, tmp_path):
    settings.FEDAPAY = {'SECRET_KEY': 'sk_sandbox_test', 'ENV': 'sandbox', 'WEBHOOK_SECRET': '', 'EXPIRATION_MINUTES': 30}
    settings.PAYPAL = {'CLIENT_ID': '', 'CLIENT_SECRET': '', 'ENV': 'sandbox'}
    settings.PAIEMENTS_PAUSE_EMAIL = 0
    settings.MEDIA_ROOT = tmp_path
    f = Faux()
    monkeypatch.setattr(fedapay, 'client', mock.Mock(return_value=f))
    monkeypatch.setattr(paypal, 'client', mock.Mock(return_value=f))
    return f


@pytest.fixture
def ong():
    o = OrganisationModel.objects.create(
        nom='Puits pour tous', slug='puits-pour-tous', cause='eau', pays='BJ', ville='Natitingou', resume='Forages',
        description='Des forages.', numero_enregistrement='2019/123/MISP', verifiee_le=date(2026, 9, 1),
        verification='Récépissé et statuts vérifiés', coordonnees_reversement='IBAN BJ00 SECRET',
    )
    ProjetModel.objects.create(organisation=o, titre='Forage de Tanguiéta', cause='eau', resume='Un forage', objectif=100_000)
    return o


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _donner(client, ong, **champs):
    corps = {'organisation': ong.slug, 'montant': 2000, 'moyen': 'mobile_money', **champs}
    r = client.post(f'{GIVE}dons/', corps, format='json')
    assert r.status_code == 201, r.data
    return DonModel.objects.get(pk=r.data['id'])


# --- Donation and payment ---------------------------------------------------------------------

def test_don_paye_frais_ajoutes(faux, make_user, ong):
    donateur = _client(make_user(email='ama@test.kwaba'))
    don = _donner(donateur, ong)
    assert (don.frais, don.total, don.montant_ong, don.statut) == (62, 2062, 2000, 'en_attente')
    assert faux.dernier['montant'] == 2062
    assert 'puits-pour-tous' not in faux.dernier['description']  # readable name, not the slug

    # The donor comes back: the payment is read again from FedaPay
    r = donateur.get(f'{GIVE}dons/{don.id}/')
    assert r.data['statut'] == 'paye' and r.data['date_reversement']
    paiement = PaiementModel.objects.get(don_id=don.id)
    assert paiement.payeur.email == 'ama@test.kwaba' and paiement.libelle == 'Don à Puits pour tous'
    assert (paiement.type_objet, paiement.objet_id) == ('don', don.id) and paiement.reference == don.reference

    # The worker sends the confirmation, only once
    services.passe()
    services.passe()
    recus = [m for m in mail.outbox if m.subject == 'Merci pour votre don à Puits pour tous']
    assert len(recus) == 1 and 'Ce n\'est pas un reçu fiscal' in recus[0].body

    historique = donateur.get(f'{GIVE}dons/').data
    assert historique['total_donne'] == 2000 and historique['nb_payes'] == 1
    assert historique['results'][0]['organisation']['slug'] == ong.slug


def test_don_frais_deduits_pour_un_projet(faux, make_user, ong):
    projet = ong.projets.get()
    don = _donner(_client(make_user()), ong, montant=5000, couvre_frais=False, projet=str(projet.id), partage_identite=True)
    assert (don.total, don.montant_ong, don.projet, don.partage_identite) == (5000, 4850, projet, True)


def test_paiement_refuse_puis_abandon(faux, make_user, ong):
    client = _client(make_user())
    faux.statut = 'declined'
    don = _donner(client, ong)
    assert client.get(f'{GIVE}dons/{don.id}/').data['statut'] == 'echoue'
    assert client.get(f'{GIVE}dons/').data['count'] == 0  # uncompleted donations hidden

    # Payment never confirmed: not completed after 24 h
    faux.statut = 'pending'
    reste = _donner(client, ong)
    DonModel.objects.filter(pk=reste.pk).update(cree_le=timezone.now() - timedelta(hours=25))
    assert services.abandonner() == 1
    reste.refresh_from_db()
    assert reste.statut == 'echoue'


def test_echec_constate_par_le_worker(faux, make_user, ong):
    faux.statut = 'pending'
    don = _donner(_client(make_user()), ong)
    PaiementModel.objects.filter(don_id=don.id).update(statut='echoue')
    assert services.passe()['dons_non_aboutis'] == 1


def test_paiement_tardif_accepte(faux, make_user, ong):
    faux.statut = 'pending'
    don = _donner(_client(make_user()), ong)
    DonModel.objects.filter(pk=don.pk).update(statut='echoue')
    faux.statut = 'approved'
    paiements.synchroniser_paiement(PaiementModel.objects.get(don_id=don.id))
    don.refresh_from_db()
    assert don.statut == 'paye' and don.paye_le
    services.paiement_recu(PaiementModel.objects.get(don_id=don.id))  # second notification: no effect


def test_refus(faux, make_user, ong, settings):
    client = _client(make_user())
    assert client.post(f'{GIVE}dons/', {'organisation': ong.slug, 'montant': 100, 'moyen': 'mobile_money'}, format='json').status_code == 400
    assert client.post(f'{GIVE}dons/', {'organisation': 'inconnue', 'montant': 1000, 'moyen': 'mobile_money'}, format='json').status_code == 400
    assert APIClient().post(f'{GIVE}dons/', {}, format='json').status_code == 401
    assert client.get(f'{GIVE}dons/00000000-0000-0000-0000-000000000000/').status_code == 404

    # Project of another NGO
    autre = OrganisationModel.objects.create(nom='Autre', slug='autre', cause='sante', pays='TG', ville='Lomé', resume='r',
                                             description='d', numero_enregistrement='1', verifiee_le=date(2026, 1, 1))
    projet_autre = ProjetModel.objects.create(organisation=autre, titre='P', cause='sante', resume='r')
    r = client.post(f'{GIVE}dons/', {'organisation': ong.slug, 'montant': 1000, 'moyen': 'mobile_money', 'projet': str(projet_autre.id)},
                    format='json')
    assert r.status_code == 400 and 'projet' in r.data['detail']

    # Provider down: no donation saved
    faux.erreur = True
    r = client.post(f'{GIVE}dons/', {'organisation': ong.slug, 'montant': 1000, 'moyen': 'mobile_money'}, format='json')
    assert r.status_code == 400 and not DonModel.objects.exists()
    # Method not enabled, then online payment disabled
    r = client.post(f'{GIVE}dons/', {'organisation': ong.slug, 'montant': 1000, 'moyen': 'paypal'}, format='json')
    assert r.status_code == 400
    settings.FEDAPAY = {**settings.FEDAPAY, 'SECRET_KEY': ''}
    r = client.post(f'{GIVE}dons/', {'organisation': ong.slug, 'montant': 1000, 'moyen': 'mobile_money'}, format='json')
    assert r.status_code == 400 and 'indisponibles' in r.data['detail']


def test_services_refusent_une_ong_non_publiee(faux, make_user, ong):
    ong.verifiee_le = None
    ong.save()
    with pytest.raises(services.DonErreur):
        services.donner(donateur=make_user(), organisation=ong, montant=1000, couvre_frais=True, moyen='mobile_money')
    ong.verifiee_le = date(2026, 9, 1)
    with pytest.raises(services.DonErreur):
        services.donner(donateur=make_user(), organisation=ong, montant=10,
                        couvre_frais=True, moyen='mobile_money')


# --- Reversements ------------------------------------------------------------------------

def _don_paye(make_user, ong, quand, montant=2000):
    don = DonModel.objects.create(donateur_id=make_user().pk, organisation=ong, montant=montant, frais=0, total=montant,
                                  montant_ong=montant, statut='paye', paye_le=quand)
    return don


def test_reversement_mensuel(faux, make_user, ong):
    make_user(role='admin', email='admin@test.kwaba')
    septembre = timezone.make_aware(datetime(2026, 9, 15, 12))
    d1 = _don_paye(make_user, ong, septembre)
    _don_paye(make_user, ong, septembre + timedelta(days=3), montant=3000)
    _don_paye(make_user, ong, timezone.make_aware(datetime(2026, 10, 2, 12)))  # current month: not yet

    assert services.preparer_reversements(date(2026, 10, 5)) == 2
    r = ReversementModel.objects.get()
    assert (r.periode, r.montant, r.nb_dons, r.date_prevue) == (date(2026, 9, 1), 5000, 2, date(2026, 10, 10))
    assert services.preparer_reversements(date(2026, 10, 5)) == 0  # idempotent

    from apps.give import notifications
    notifications.envoyer_notifications()
    assert any('Reversement à effectuer' in m.subject for m in mail.outbox)

    # Done: the donors are notified and the proof is public
    r.justificatif = SimpleUploadedFile('preuve.pdf', b'%PDF-1.4', content_type='application/pdf')
    r.save()
    services.marquer_effectue(r, moyen='virement', reference_operation='VIR-001')
    services.marquer_effectue(r, moyen='virement', reference_operation='autre')  # already done: no effect
    assert ReversementModel.objects.get().reference_operation == 'VIR-001'
    mail.outbox.clear()
    notifications.envoyer_notifications()
    assert len([m for m in mail.outbox if m.subject.startswith('Votre don a été reversé')]) == 2

    donateur = _client(d1.donateur)
    suivi = donateur.get(f'{GIVE}dons/').data['results'][0]['reversement']
    assert suivi['statut'] == 'effectue' and suivi['justificatif'].endswith('.pdf')
    page = APIClient().get(f'{GIVE}organisations/{ong.slug}/').data
    assert page['impact'] == {'collecte': 7000, 'reverse': 5000, 'en_attente': 2000, 'nb_dons': 3, 'nb_donateurs': 3}
    assert page['reversements'][0]['reference_operation'] == 'VIR-001'
    assert 'coordonnees_reversement' not in page and 'SECRET' not in str(page)

    # September donation confirmed after the transfer: it goes with the following month
    _don_paye(make_user, ong, septembre + timedelta(days=10))
    services.preparer_reversements(date(2026, 11, 3))
    octobre = ReversementModel.objects.get(periode=date(2026, 10, 1))
    assert octobre.nb_dons == 2 and octobre.montant == 4000


def test_impact_public(faux, make_user, ong):
    _don_paye(make_user, ong, timezone.now())
    data = APIClient().get(f'{GIVE}impact/').data
    assert data['collecte'] == 2000 and data['nb_organisations'] == 1
    assert next(c for c in data['causes'] if c['code'] == 'eau')['collecte'] == 2000


# --- API publique ------------------------------------------------------------------------

def test_catalogue_public(faux, make_user, ong):
    cachee = OrganisationModel.objects.create(nom='En cours', slug='en-cours', cause='eau', pays='TG', ville='Lomé', resume='r',
                                              description='d', numero_enregistrement='1')
    anonyme = APIClient()
    config = anonyme.get(f'{GIVE}config/').data
    assert config['montants_suggeres'] == [500, 2000, 3000, 5000] and config['commission_kwaba'] == 0
    assert config['moyens'] == ['mobile_money', 'carte']

    liste = anonyme.get(f'{GIVE}organisations/').data
    assert [o['slug'] for o in liste['results']] == [ong.slug]  # not verified: invisible
    assert anonyme.get(f'{GIVE}organisations/', {'cause': 'sante'}).data['count'] == 0
    assert anonyme.get(f'{GIVE}organisations/{cachee.slug}/').status_code == 404
    detail = anonyme.get(f'{GIVE}organisations/{ong.slug}/').data
    assert detail['projets'][0]['objectif'] == 100_000 and detail['numero_enregistrement'] == '2019/123/MISP'


def test_slug_reserve():
    o = OrganisationModel(nom='X', slug='impact', cause='eau', pays='TG', ville='Lomé', resume='r', description='d',
                          numero_enregistrement='1')
    with pytest.raises(ValidationError):
        o.full_clean()
    assert not o.publiee and str(o) == 'X'


@pytest.mark.parametrize('adresse, statut', [
    ('https://ong.example', 200),
    ('http://ong.example', 200),
    ('ftp://ong.example', 400),
    ('javascript:alert(1)', 400),
])
def test_site_web_en_http_seulement(make_user, ong, adresse, statut):
    admin = _client(make_user(role='admin', is_staff=True, is_superuser=True))
    r = admin.patch(f'/api/v1/admin/give/organisations/{ong.pk}/', {'site_web': adresse}, format='json')
    assert r.status_code == statut, r.data


# --- Admin and demo --------------------------------------------------------------

def test_admin(faux, make_user, ong):
    admin = make_user(role='admin', is_staff=True, is_superuser=True)
    don = _don_paye(make_user, ong, timezone.make_aware(datetime(2026, 8, 3, 12)))
    navigateur = Client()
    navigateur.force_login(admin)
    for url in ('/admin/give/organisationmodel/', f'/admin/give/organisationmodel/{ong.pk}/change/', '/admin/give/donmodel/',
                f'/admin/give/donmodel/{don.pk}/change/', '/admin/give/reversementmodel/'):
        assert navigateur.get(url).status_code == 200, url

    navigateur.post('/admin/give/donmodel/', {'action': 'preparer_reversements', '_selected_action': [don.pk]})
    r = ReversementModel.objects.get()
    page = navigateur.get(f'/admin/give/reversementmodel/{r.pk}/change/').content.decode()
    assert 'IBAN BJ00 SECRET' in page and 'Anonyme' in page  # contact details visible to the team, anonymous donor

    url = f'/admin/give/reversementmodel/{r.pk}/change/'
    # Without proof: refused
    navigateur.post(url, {'statut': 'effectue', 'moyen': 'virement', 'reference_operation': '', 'note': '',
                          'dons-TOTAL_FORMS': 1, 'dons-INITIAL_FORMS': 1, 'dons-0-id': don.pk, 'dons-0-reversement': r.pk})
    assert ReversementModel.objects.get().statut == 'a_effectuer'
    navigateur.post(url, {'statut': 'effectue', 'moyen': 'virement', 'reference_operation': 'VIR-9', 'note': 'Merci !',
                          'justificatif': SimpleUploadedFile('preuve.pdf', b'%PDF-1.4', content_type='application/pdf'),
                          'dons-TOTAL_FORMS': 1, 'dons-INITIAL_FORMS': 1, 'dons-0-id': don.pk, 'dons-0-reversement': r.pk})
    r.refresh_from_db()
    assert r.statut == 'effectue' and r.effectue_le == timezone.localdate()
    assert str(r).startswith('Puits pour tous') and str(don).startswith('DON-')


def test_commande_de_demonstration():
    call_command('seed_give_demo')
    call_command('seed_give_demo')
    assert OrganisationModel.objects.filter(slug__startswith='demo-').count() == 4
    assert str(ProjetModel.objects.first())
