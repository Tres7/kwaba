"""Car and driver hire (PostgreSQL). FedaPay is simulated: no network call."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.core import mail
from django.utils import timezone

from apps.locations import services
from apps.locations.models import (
    CategorieVehiculeModel, LieuRemiseModel, LocationModel, ParametresLocationModel, PartenaireLocationModel,
    VersementChauffeurLocationModel, VersementPartenaireModel,
)
from apps.paiements import fedapay
from apps.paiements import services as paiements
from apps.paiements.models import PaiementModel, RemboursementModel
from apps.transferts.api import fiche_chauffeur
from apps.transferts.models import ChauffeurModel

LOCATIONS = '/api/v1/locations/'
FEDAPAY_TEST = {'SECRET_KEY': 'sk_sandbox_test', 'ENV': 'sandbox', 'WEBHOOK_SECRET': '', 'EXPIRATION_MINUTES': 30}


class FauxFedaPay:
    def __init__(self):
        self.statut = 'pending'
        self.payouts = []

    def creer_transaction(self, **kwargs):
        self.transaction = kwargs
        self.numero = getattr(self, 'numero', 887) + 1  # one id per transaction (several payments per test)
        return str(self.numero), f'https://sandbox-process.fedapay.com/{self.numero}'

    def lire_transaction(self, identifiant):
        return {'id': identifiant, 'status': self.statut, 'mode': 'momo_test'}

    def creer_versement(self, **kwargs):
        self.payouts.append(kwargs)
        return f'P{len(self.payouts)}'

    def lire_versement(self, identifiant):
        return {'id': identifiant, 'status': 'sent'}


@pytest.fixture
def faux(settings, monkeypatch):
    settings.FEDAPAY = FEDAPAY_TEST
    settings.PAYPAL = {'CLIENT_ID': '', 'CLIENT_SECRET': '', 'ENV': 'sandbox'}
    settings.PAIEMENTS_PAUSE_EMAIL = 0
    f = FauxFedaPay()
    monkeypatch.setattr(fedapay, 'client', mock.Mock(return_value=f))
    return f


@pytest.fixture
def catalogue():
    """Setup by the administration: rules, an owner's vehicle (price and deposit), two places."""
    ParametresLocationModel.objects.create(
        commission_pourcent=Decimal('15'), delai_min_jours=2, duree_max_jours=30, annulation_gratuite_heures=48,
        conditions='23 ans minimum, permis depuis 2 ans.',
    )
    aeroport = LieuRemiseModel.objects.create(nom='Aéroport de Lomé', ville='Lomé', fuseau='Africa/Lome', frais=5000)
    livraison = LieuRemiseModel.objects.create(nom='Livraison à votre adresse, Lomé', ville='Lomé', fuseau='Africa/Lome',
                                               adresse_requise=True, frais=3000)
    proprietaire = PartenaireLocationModel.objects.create(
        nom='Lomé Auto Location', contact='Yao Mensah', telephone='+228 90 44 55 66', email='yao@test.kwaba',
        pays_versement='TG', operateur_versement='togocel', numero_versement='90445566',
    )
    proprietaire.lieux.add(aeroport)
    berline = CategorieVehiculeModel.objects.get(nom='Berline')  # created without a price by the migration
    berline.proprietaire, berline.prix_jour, berline.caution_jours = proprietaire, 30000, 2
    berline.exemple_modele, berline.immatriculation = 'Toyota Corolla', 'TG-5678-CD'
    berline.sans_chauffeur = berline.avec_chauffeur = berline.actif = True
    berline.save()
    return {'berline': berline, 'aeroport': aeroport, 'livraison': livraison, 'proprietaire': proprietaire}


@pytest.fixture
def loueur(catalogue):
    return catalogue['proprietaire']


@pytest.fixture
def chauffeur():
    return ChauffeurModel.objects.create(
        prenom='Kodjo', nom='Afi', telephone='+228 91 00 00 00', email='kodjo@test.kwaba', categorie='berline',
        vehicule='Toyota Corolla', immatriculation='TG-1', pays_versement='TG', operateur_versement='togocel',
        numero_versement='91000000',
    )


def _date(jours=5, heure='10:00'):
    return f"{(timezone.localdate() + timedelta(days=jours)).isoformat()}T{heure}"


def _demande(catalogue, **champs):
    return {
        'categorie': catalogue['berline'].id, 'formule': 'avec_chauffeur', 'lieu_prise': catalogue['aeroport'].id,
        'lieu_retour': catalogue['aeroport'].id, 'debut': _date(5, '10:00'), 'fin': _date(8, '12:00'), 'passagers': 3,
        'telephone': '+33 6 12 34 56 78', 'precisions': 'Trajets Lomé - Kpalimé, un siège enfant pour 2 ans.', **champs,
    }


def _reserver_et_payer(client, faux, catalogue, **champs):
    r = client.post(LOCATIONS, _demande(catalogue, **champs), format='json')
    assert r.status_code == 201, r.data
    lid = r.data['id']
    assert client.post(f'{LOCATIONS}{lid}/payer/', {'moyen': 'mobile_money'}, format='json').status_code == 200
    faux.statut = 'approved'
    assert client.get(f'{LOCATIONS}{lid}/').data['statut'] == 'confirmee'
    return LocationModel.objects.get(pk=lid)


def _payes(*locations):
    """Due dates reached: the payouts go at the next pass."""
    for modele in (VersementPartenaireModel, VersementChauffeurLocationModel):
        modele.objects.filter(location__in=locations).update(date_prevue=timezone.now() - timedelta(minutes=1))


class TestCatalogue:
    def test_nothing_offered_until_the_admin_sets_it_up(self, api_client):
        # Typical vehicles created by the migration, but without a price and inactive
        assert CategorieVehiculeModel.objects.filter(gamme='suv').exists()
        assert api_client.get(f'{LOCATIONS}catalogue/').data == {'active': False}

    def test_only_priced_active_vehicles_are_offered(self, api_client, catalogue):
        data = api_client.get(f'{LOCATIONS}catalogue/').data
        assert data['active'] is True
        assert [c['nom'] for c in data['categories']] == ['Berline']
        berline = data['categories'][0]
        assert (berline['prix_jour'], berline['caution'], berline['formules']) == (
            30000, 60000, {'sans_chauffeur': True, 'avec_chauffeur': True})
        assert 'Lomé Auto Location' not in str(data)  # the owner is never shown
        assert data['chauffeur'] == {'prix_jour': 7000, 'prime_hors_lome': 1500, 'prime_hors_pays': 2000, 'heure_sup': 1000}
        assert data['regles']['delai_min_jours'] == 2

    def test_expired_insurance_hides_the_vehicle(self, api_client, catalogue):
        CategorieVehiculeModel.objects.filter(pk=catalogue['berline'].pk).update(assurance_fin=timezone.localdate() - timedelta(days=1))
        assert api_client.get(f'{LOCATIONS}catalogue/').data == {'active': False}

    def test_quote_counts_started_days_and_place_fees(self, api_client, catalogue):
        q = {'categorie': catalogue['berline'].id, 'formule': 'sans_chauffeur', 'lieu_prise': catalogue['aeroport'].id,
             'lieu_retour': catalogue['livraison'].id, 'debut': _date(5, '10:00'), 'fin': _date(8, '12:00')}
        devis = api_client.get(f'{LOCATIONS}devis/', q).data
        # 3 days + 2 started hours = 4 days; fees: 5,000 (airport) + 3,000 (delivery); deposit: 2 days
        assert devis == {'jours': 4, 'prix_jour': 30000, 'prix_vehicule': 120000, 'frais_lieux': 8000, 'prix_chauffeur': 0,
                         'primes': 0, 'prix': 128000, 'caution': 60000, 'caution_en_ligne': True, 'a_payer': 188000}

    def test_self_drive_refused_while_hidden(self, api_client, catalogue, settings):
        # Outside the launch offer: refused by the API while the switch is off
        settings.MODULES = {**settings.MODULES, 'location_sans_chauffeur': False}
        q = {'categorie': catalogue['berline'].id, 'formule': 'sans_chauffeur', 'lieu_prise': catalogue['aeroport'].id,
             'lieu_retour': catalogue['aeroport'].id, 'debut': _date(5, '10:00'), 'fin': _date(8, '12:00')}
        r = api_client.get(f'{LOCATIONS}devis/', q)
        assert r.status_code == 400 and 'sans chauffeur' in str(r.data)
        assert api_client.get(f'{LOCATIONS}devis/', {**q, 'formule': 'avec_chauffeur'}).status_code == 200

    def test_quote_with_driver_and_travel_allowances(self, api_client, catalogue):
        q = {'categorie': catalogue['berline'].id, 'formule': 'avec_chauffeur', 'lieu_prise': catalogue['aeroport'].id,
             'lieu_retour': catalogue['aeroport'].id, 'debut': _date(5, '10:00'), 'fin': _date(8, '12:00'),
             'jours_hors_lome': 2, 'jours_hors_pays': 1}
        devis = api_client.get(f'{LOCATIONS}devis/', q).data
        # No deposit with a driver; 4 × 7,000 for the driver; allowances 2 × 1,500 + 2,000
        assert (devis['prix_chauffeur'], devis['primes'], devis['caution'], devis['prix']) == (28000, 5000, 0, 163000)


class TestReservation:
    def test_at_least_two_days_before_pickup(self, client_for, make_user, faux, catalogue):
        r = client_for(make_user()).post(LOCATIONS, _demande(catalogue, debut=_date(1), fin=_date(3)), format='json')
        assert r.status_code == 400 and '2 jours' in r.data['detail']

    def test_customer_must_describe_the_need(self, client_for, make_user, faux, catalogue):
        r = client_for(make_user()).post(LOCATIONS, _demande(catalogue, precisions='voiture'), format='json')
        assert r.status_code == 400 and 'precisions' in r.data

    def test_self_drive_needs_driver_and_licence(self, client_for, make_user, faux, catalogue):
        client = client_for(make_user())
        r = client.post(LOCATIONS, _demande(catalogue, formule='sans_chauffeur'), format='json')
        assert r.status_code == 400 and 'permis' in r.data['detail']
        r = client.post(LOCATIONS, _demande(catalogue, formule='sans_chauffeur', conducteur='Ama Kossi',
                                            permis_numero='TG-123456', permis_pays='Togo'), format='json')
        assert r.status_code == 201 and r.data['caution'] == 60000

    def test_delivery_needs_an_address(self, client_for, make_user, faux, catalogue):
        r = client_for(make_user()).post(LOCATIONS, _demande(catalogue, lieu_prise=catalogue['livraison'].id), format='json')
        assert r.status_code == 400 and 'adresse' in r.data['detail']

    def test_too_many_passengers(self, client_for, make_user, faux, catalogue):
        r = client_for(make_user()).post(LOCATIONS, _demande(catalogue, passagers=9), format='json')
        assert r.status_code == 400

    def test_too_many_days_away(self, client_for, make_user, faux, catalogue):
        r = client_for(make_user()).post(LOCATIONS, _demande(catalogue, jours_hors_lome=3, jours_hors_pays=2), format='json')
        assert r.status_code == 400 and 'hors de Lomé' in r.data['detail']

    def test_price_is_computed_by_the_server(self, client_for, make_user, faux, catalogue):
        r = client_for(make_user()).post(LOCATIONS, _demande(catalogue, prix=1, commission=0), format='json')
        # 4 days × 30,000 + 2 × 5,000 airport fees + 4 × 7,000 for the driver
        assert (r.data['prix'], r.data['prix_chauffeur']) == (158000, 28000)

    def test_someone_else_s_rental_is_invisible(self, client_for, make_user, faux, catalogue):
        loc = _reserver_et_payer(client_for(make_user()), faux, catalogue)
        autre = client_for(make_user())
        assert autre.get(f'{LOCATIONS}{loc.id}/').status_code == 404
        assert autre.delete(f'{LOCATIONS}{loc.id}/').status_code == 404


def test_full_cycle_owner_and_driver_payouts(client_for, make_user, faux, catalogue, loueur, chauffeur):
    make_user(role='admin', email='admin@test.kwaba')
    voyageur = make_user(email='voyageur@test.kwaba')
    client = client_for(voyageur)
    loc = _reserver_et_payer(client, faux, catalogue)
    assert faux.transaction['montant'] == 158000
    assert client.get(f'{LOCATIONS}{loc.id}/').data['vehicule_attribue'] is None

    paiements.passe()
    sujets = {m.subject for m in mail.outbox}
    assert 'Réservation confirmée : Lomé' in sujets
    assert any(s.startswith('[Kwa-Ba] Location à attribuer') for s in sujets)

    assert list(services.partenaires_disponibles(loc)) == [loueur]
    with pytest.raises(services.LocationErreur, match='chauffeur'):
        services.attribuer(loc, partenaire=loueur)
    services.attribuer(loc, partenaire=loueur, chauffeur=fiche_chauffeur(chauffeur.pk))
    detail = client.get(f'{LOCATIONS}{loc.id}/').data
    assert detail['statut'] == 'partenaire_assigne'
    # The site shows the vehicle, never the owner nor the driver
    assert detail['vehicule_attribue'] == {'vehicule': 'Toyota Corolla', 'immatriculation': 'TG-5678-CD'}
    assert not any(x in str(detail) for x in ('Lomé Auto Location', 'Yao', '90 44 55 66', 'Kodjo', '91 00 00 00'))
    mail.outbox.clear()
    paiements.passe()
    emails = {m.to[0]: m.body for m in mail.outbox}
    assert set(emails) == {'voyageur@test.kwaba', 'yao@test.kwaba', 'kodjo@test.kwaba'}
    # Contact details of the owner and the driver: by email to the traveller, after the payment
    assert '+228 90 44 55 66' in emails['voyageur@test.kwaba'] and '+228 91 00 00 00' in emails['voyageur@test.kwaba']
    # Neither the owner nor the driver have the traveller's phone: they go through Kwa-Ba
    assert all('12 34 56 78' not in emails[e] for e in ('yao@test.kwaba', 'kodjo@test.kwaba'))
    assert 'siège enfant' in emails['kodjo@test.kwaba'] and '24 000' in emails['kodjo@test.kwaba']

    v = VersementPartenaireModel.objects.get(location=loc)
    assert (v.montant_brut, v.commission, v.montant) == (130000, 18000, 112000)  # 15 % of the vehicle price
    vc = VersementChauffeurLocationModel.objects.get(location=loc)
    assert (vc.montant_brut, vc.commission, vc.montant) == (28000, 4000, 24000)  # 6,000 per day for the driver
    _payes(loc)
    paiements.passe()  # envoi
    paiements.passe()  # FedaPay confirms: paid, rental finished
    assert sorted(p['montant'] for p in faux.payouts) == [24000, 112000]
    loc.refresh_from_db()
    assert loc.statut == 'terminee'


def test_driver_only_for_the_customer_s_car(client_for, make_user, faux, catalogue, chauffeur):
    client = client_for(make_user())
    loc = _reserver_et_payer(client, faux, catalogue, categorie=None, formule='chauffeur_seul',
                             lieu_prise=catalogue['livraison'].id, lieu_retour=catalogue['livraison'].id,
                             adresse_prise='Bè Kpota, rue 12', adresse_retour='Bè Kpota, rue 12',
                             jours_hors_lome=1, jours_hors_pays=1)
    # 4 × 7,000 + 1,500 + 2,000; no vehicle, no handover fees, no deposit
    assert (loc.categorie_id, loc.prix, loc.frais_lieux, loc.caution) == (None, 31500, 0, 0)
    assert services.partenaires_disponibles(loc).count() == 0
    services.attribuer(loc, chauffeur=fiche_chauffeur(chauffeur.pk))
    vc = VersementChauffeurLocationModel.objects.get(location=loc)
    assert (vc.montant_brut, vc.commission, vc.montant) == (31500, 4000, 27500)  # allowances fully paid
    assert not VersementPartenaireModel.objects.filter(location=loc).exists()
    assert client.get(f'{LOCATIONS}{loc.id}/').data['libelle'] == 'Chauffeur pour votre véhicule'


def test_my_driver_and_excellence_pay_6500_a_day(client_for, make_user, faux, catalogue, loueur, chauffeur):
    voyageur = make_user()
    client = client_for(voyageur)
    ancienne = _reserver_et_payer(client, faux, catalogue)
    services.attribuer(ancienne, partenaire=loueur, chauffeur=fiche_chauffeur(chauffeur.pk))
    autre = ChauffeurModel.objects.create(prenom='Afi', nom='Dzifa', telephone='+228 92 00 00 00', categorie='berline',
                                          vehicule='-', immatriculation='-', pays_versement='TG',
                                          operateur_versement='togocel', numero_versement='92000000')
    # Only a driver who has already driven us can be asked for again
    assert client.post(LOCATIONS, _demande(catalogue, chauffeur_demande=chauffeur.id), format='json').status_code == 400
    LocationModel.objects.filter(pk=ancienne.pk).update(statut='terminee')
    assert client.get(f'{LOCATIONS}mes-chauffeurs/').data == [{'id': chauffeur.id, 'nom': 'Kodjo A.'}]

    loc = _reserver_et_payer(client, faux, catalogue, chauffeur_demande=chauffeur.id)
    services.attribuer(loc, partenaire=loueur, chauffeur=fiche_chauffeur(chauffeur.pk))
    assert VersementChauffeurLocationModel.objects.get(location=loc).montant == 26000  # 4 × 6 500
    ChauffeurModel.objects.filter(pk=autre.pk).update(excellence=True)
    services.attribuer(loc, partenaire=loueur, chauffeur=fiche_chauffeur(autre.pk))
    assert VersementChauffeurLocationModel.objects.get(location=loc).montant == 26000  # Excellence


def test_founding_owner_and_loyal_customer(client_for, make_user, faux, catalogue, loueur):
    jour = timezone.localdate()
    PartenaireLocationModel.objects.filter(pk=loueur.pk).update(fondateur_debut=jour, fondateur_fin=jour + timedelta(days=180))
    voyageur = make_user()
    for _ in range(3):  # three rentals finished without incident
        LocationModel.objects.create(
            voyageur_id=voyageur.pk, categorie=catalogue['berline'], formule='sans_chauffeur', lieu_prise=catalogue['aeroport'],
            lieu_retour=catalogue['aeroport'], debut=timezone.now() - timedelta(days=10), fin=timezone.now() - timedelta(days=8),
            passagers=1, telephone='+22890000000', precisions='-', jours=2, prix_jour=30000, frais_lieux=0, prix=60000,
            commission=9000, statut='terminee',
        )
    r = client_for(voyageur).post(LOCATIONS, _demande(catalogue, formule='sans_chauffeur', conducteur='Ama Kossi',
                                                      permis_numero='TG-123456', permis_pays='Togo'), format='json')
    assert r.status_code == 201, r.data
    loc = LocationModel.objects.get(pk=r.data['id'])
    assert loc.caution == 30000  # deposit halved
    assert loc.commission == 12000  # 10 % during the Founders Programme


def test_stay_pack_lowers_the_accommodation_fee_to_3_percent(client_for, make_user, faux, catalogue, make_hebergement, make_reservation):
    voyageur = make_user()
    sejour = make_reservation(make_hebergement(), guest=voyageur, starts_in=6, nights=2)
    sejour.prix_nuits, sejour.frais_service, sejour.commission_hote, sejour.total_price = 50000, 3000, 4000, 53000
    sejour.save()
    PaiementModel.objects.create(reservation_id=sejour.id, montant=53000, statut='reussi', transaction_id='T-SEJOUR')
    _reserver_et_payer(client_for(voyageur), faux, catalogue, reservation=str(sejour.id))
    sejour.refresh_from_db()
    assert (sejour.frais_service, sejour.total_price) == (1500, 51500)
    rb = RemboursementModel.objects.get(reservation_id=sejour.id)
    assert rb.montant == 1500 and 'Pack Séjour' in rb.motif


def test_contacts_in_free_text_are_masked_for_the_partner(client_for, make_user, faux, catalogue, loueur, chauffeur):
    client = client_for(make_user())
    loueur.lieux.add(catalogue['livraison'])
    loc = _reserver_et_payer(client, faux, catalogue, lieu_prise=catalogue['livraison'].id,
                             adresse_prise='Bè Kpota, appelez le 90 11 22 33',
                             precisions='Siège enfant svp, écrivez-moi sur ama.k@gmail.com ou au 99 88 77 66.')
    services.attribuer(loc, partenaire=loueur, chauffeur=fiche_chauffeur(chauffeur.pk))
    mail.outbox.clear()
    paiements.passe()
    for destinataire in ('yao@test.kwaba', 'kodjo@test.kwaba'):
        corps = next(m.body for m in mail.outbox if m.to == [destinataire])
        assert 'Bè Kpota' in corps and 'Siège enfant' in corps
        assert not any(x in corps for x in ('90 11 22 33', '99 88 77 66', 'ama.k@gmail.com'))


def test_free_cancellation_then_refund_to_the_given_number(client_for, make_user, faux, catalogue, loueur, chauffeur):
    client = client_for(make_user())
    loc = _reserver_et_payer(client, faux, catalogue)
    services.attribuer(loc, partenaire=loueur, chauffeur=fiche_chauffeur(chauffeur.pk))
    assert client.get(f'{LOCATIONS}{loc.id}/').data['rembourse_si_annulation'] == loc.prix
    r = client.delete(f'{LOCATIONS}{loc.id}/')
    assert r.data['rembourse'] == loc.prix and r.data['numero_requis'] is True
    assert VersementPartenaireModel.objects.get(location=loc).statut == 'annule'
    assert VersementChauffeurLocationModel.objects.get(location=loc).statut == 'annule'
    url = f'{LOCATIONS}{loc.id}/compte-remboursement/'
    assert client.put(url, {'pays': 'TG', 'operateur': 'moov_tg', 'numero': '96000001'}, format='json').status_code == 200
    paiements.envoyer_remboursements()
    assert faux.payouts[-1]['client']['phone_number'] == {'number': '96000001', 'country': 'tg'}


def test_cancellation_between_48_and_24_hours_refunds_half(client_for, make_user, faux, catalogue, loueur, chauffeur):
    client = client_for(make_user())
    loc = _reserver_et_payer(client, faux, catalogue)
    services.attribuer(loc, partenaire=loueur, chauffeur=fiche_chauffeur(chauffeur.pk))
    LocationModel.objects.filter(pk=loc.pk).update(debut=timezone.now() + timedelta(hours=30))
    assert client.delete(f'{LOCATIONS}{loc.id}/').data['rembourse'] == 79000
    v = VersementPartenaireModel.objects.get(location=loc)
    assert (v.statut, v.montant_brut, v.commission, v.montant) == ('planifie', 65000, 9000, 56000)
    vc = VersementChauffeurLocationModel.objects.get(location=loc)
    assert (vc.statut, vc.montant) == ('planifie', 12000)  # half of their share is still paid to them
    _payes(loc)
    paiements.passe()
    assert sorted(p['montant'] for p in faux.payouts) == [12000, 56000]


def test_late_cancellation_keeps_the_partners_paid(client_for, make_user, faux, catalogue, loueur, chauffeur):
    client = client_for(make_user())
    loc = _reserver_et_payer(client, faux, catalogue)
    services.attribuer(loc, partenaire=loueur, chauffeur=fiche_chauffeur(chauffeur.pk))
    LocationModel.objects.filter(pk=loc.pk).update(debut=timezone.now() + timedelta(hours=20))
    assert client.delete(f'{LOCATIONS}{loc.id}/').data['rembourse'] == 0
    assert not RemboursementModel.objects.filter(location_id=loc.id).exists()
    assert VersementPartenaireModel.objects.get(location=loc).statut == 'planifie'
    assert VersementChauffeurLocationModel.objects.get(location=loc).montant == 24000


def test_cancellation_by_kwaba_refunds_everything(client_for, make_user, faux, catalogue):
    loc = _reserver_et_payer(client_for(make_user()), faux, catalogue)
    LocationModel.objects.filter(pk=loc.pk).update(debut=timezone.now() + timedelta(hours=20))
    assert services.annuler(LocationModel.objects.get(pk=loc.pk), par='plateforme') == loc.prix


def test_unpaid_rental_expires(client_for, make_user, faux, catalogue):
    r = client_for(make_user()).post(LOCATIONS, _demande(catalogue), format='json')
    LocationModel.objects.filter(pk=r.data['id']).update(expire_le=timezone.now() - timedelta(minutes=1))
    assert services.expirer() == 1
    loc = LocationModel.objects.get(pk=r.data['id'])
    assert (loc.statut, loc.annulee_par) == ('annulee', 'expiration')


# --- Deposit paid online and kept by Kwa-Ba ---------------------------------------------------------------

SANS_CHAUFFEUR = {'formule': 'sans_chauffeur', 'conducteur': 'Ama Kossi', 'permis_numero': 'TG-123456', 'permis_pays': 'Togo'}


def _vehicule_rendu(loc, heures=25):
    """The vehicle was picked up 3 days ago and returned `heures` hours ago."""
    maintenant = timezone.now()
    LocationModel.objects.filter(pk=loc.pk).update(debut=maintenant - timedelta(days=3), fin=maintenant - timedelta(hours=heures))
    VersementPartenaireModel.objects.filter(location=loc).update(date_prevue=maintenant - timedelta(minutes=1))
    loc.refresh_from_db()
    return loc


def test_deposit_paid_online_then_refunded_minus_damages(client_for, make_user, faux, catalogue, loueur):
    client = client_for(make_user(email='ama@test.kwaba'))
    loc = _reserver_et_payer(client, faux, catalogue, **SANS_CHAUFFEUR)
    # 4 days × 30,000 + 2 × 5,000 fees, plus a 60,000 deposit (two days) paid with the rental
    assert (loc.prix, loc.caution, loc.caution_en_ligne) == (130000, 60000, True)
    assert faux.transaction['montant'] == 190000
    detail = client.get(f'{LOCATIONS}{loc.id}/').data
    assert detail['a_payer'] == 190000 and detail['caution_etat']['restituee'] is False

    services.attribuer(loc, partenaire=loueur, vehicule='Toyota Yaris grise')
    mail.outbox.clear()
    paiements.passe()
    au_loueur = next(m.body for m in mail.outbox if m.to == ['yao@test.kwaba'])
    assert 'ne lui demandez rien' in au_loueur and 'Signalez-le à Kwa-Ba dans les 24 heures' in au_loueur

    loc = _vehicule_rendu(loc, heures=2)
    services.retenir_caution(loc, 30000, 'Rétroviseur cassé')
    v = VersementPartenaireModel.objects.get(location=loc)
    assert (v.montant_brut, v.commission, v.montant) == (160000, 18000, 142000)  # the withheld amount is added, without commission
    paiements.passe()
    loc.refresh_from_db()
    assert loc.caution_restituee_le is None and faux.payouts == []  # reporting period not over: nothing goes out

    loc = _vehicule_rendu(loc, heures=25)
    mail.outbox.clear()
    paiements.passe()
    loc.refresh_from_db()
    assert loc.caution_restituee_le is not None
    rb = RemboursementModel.objects.get(location_id=loc.id)
    assert (rb.montant, rb.motif, rb.statut) == (30000, 'Restitution de la caution', 'attente_numero')
    au_voyageur = next(m for m in mail.outbox if m.to == ['ama@test.kwaba'] and 'caution' in m.subject)
    assert '30 000' in au_voyageur.body and 'Rétroviseur cassé' in au_voyageur.body and 'numéro Mobile Money' in au_voyageur.body
    assert [p['montant'] for p in faux.payouts] == [142000]  # owner paid with the withheld amount
    with pytest.raises(services.LocationErreur):
        services.retenir_caution(loc, 10000, 'Trop tard')


def test_deposit_retention_rules(client_for, make_user, faux, catalogue, loueur):
    loc = _reserver_et_payer(client_for(make_user()), faux, catalogue, **SANS_CHAUFFEUR)
    services.attribuer(loc, partenaire=loueur)
    with pytest.raises(services.LocationErreur, match='pas encore été remis'):
        services.retenir_caution(loc, 10000, 'Rayure')
    loc = _vehicule_rendu(loc, heures=2)
    with pytest.raises(services.LocationErreur, match='entre 0 et la caution'):
        services.retenir_caution(loc, 60001, 'Trop')
    with pytest.raises(services.LocationErreur, match='motif'):
        services.retenir_caution(loc, 10000, '  ')
    services.retenir_caution(loc, 10000, 'Rayure')
    services.retenir_caution(loc, 0, '')  # cancels the withheld amount
    loc.refresh_from_db()
    assert (loc.caution_retenue, loc.caution_motif) == (0, '')
    assert VersementPartenaireModel.objects.get(location=loc).montant == loc.montant_partenaire


def test_back_office_records_a_retention(client_for, make_user, faux, catalogue, loueur):
    loc = _reserver_et_payer(client_for(make_user()), faux, catalogue, **SANS_CHAUFFEUR)
    services.attribuer(loc, partenaire=loueur)
    loc = _vehicule_rendu(loc, heures=2)
    admin = client_for(make_user(role='admin'))
    url = f'/api/v1/admin/location/locations/{loc.id}/caution/'
    assert client_for(make_user()).post(url, {'montant': 5000, 'motif': 'Plein non fait'}, format='json').status_code == 403
    r = admin.post(url, {'montant': 5000, 'motif': 'Plein non fait'}, format='json')
    assert r.status_code == 200 and (r.data['caution_retenue'], r.data['caution_motif']) == (5000, 'Plein non fait')
    assert admin.post(url, {'montant': 200000, 'motif': 'Trop'}, format='json').status_code == 400


def test_cancelled_rental_always_refunds_the_deposit(client_for, make_user, faux, catalogue, loueur):
    client = client_for(make_user())
    loc = _reserver_et_payer(client, faux, catalogue, **SANS_CHAUFFEUR)
    services.attribuer(loc, partenaire=loueur)
    LocationModel.objects.filter(pk=loc.pk).update(debut=timezone.now() + timedelta(hours=20))
    # Less than 24 h before: the rental is not refunded, the deposit is
    assert client.delete(f'{LOCATIONS}{loc.id}/').data['rembourse'] == 60000
    assert VersementPartenaireModel.objects.get(location=loc).statut == 'planifie'


def test_deposit_paid_to_the_partner_when_online_deposit_is_off(client_for, make_user, faux, catalogue, loueur):
    ParametresLocationModel.objects.filter(pk=1).update(caution_en_ligne=False)
    client = client_for(make_user())
    loc = _reserver_et_payer(client, faux, catalogue, **SANS_CHAUFFEUR)
    assert faux.transaction['montant'] == 130000 and loc.caution_en_ligne is False
    assert client.get(f'{LOCATIONS}{loc.id}/').data['caution_etat'] is None
    services.attribuer(loc, partenaire=loueur)
    mail.outbox.clear()
    paiements.passe()
    au_loueur = next(m.body for m in mail.outbox if m.to == ['yao@test.kwaba'])
    assert 'Caution à encaisser à la remise : 60 000' in au_loueur
