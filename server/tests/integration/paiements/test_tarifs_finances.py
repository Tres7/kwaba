"""Back-office: rates changed without a deployment (AN-B1), contracts that follow them, finances of a period (AN-B2)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.contrats import services as contrats
from apps.contrats.models import ModeleContratModel
from apps.paiements.models import FraisMenageModel, PaiementModel, ReglagesTarifsModel, RemboursementModel, VersementModel
from apps.reservations.models import ReservationModel
from apps.activity.models import ActivityEntryModel

TARIFS = '/api/v1/admin/paiements/tarifs/'
FINANCES = '/api/v1/admin/paiements/finances/'


@pytest.fixture(autouse=True)
def sans_paiement_en_ligne(settings):
    settings.FEDAPAY = {**settings.FEDAPAY, 'SECRET_KEY': ''}
    settings.PAYPAL = {**settings.PAYPAL, 'CLIENT_ID': '', 'CLIENT_SECRET': ''}


@pytest.fixture
def admin(client_for, make_user):
    return client_for(make_user(role='admin'))


def _reserver(client, hebergement, dans=20, nuits=2):
    debut = timezone.localdate() + timedelta(days=dans)
    r = client.post('/api/v1/reservations/', {'hebergement': str(hebergement.id), 'check_in': debut.isoformat(),
                                               'check_out': (debut + timedelta(days=nuits)).isoformat(), 'guests_count': 1})
    assert r.status_code == 201, r.data
    return ReservationModel.objects.get(pk=r.data['id'])


class TestTarifs:
    def test_grid_in_force(self, admin):
        d = admin.get(TARIFS).data
        assert d['taux'] == {'frais_voyageur': 6.0, 'frais_reduits': 3.0, 'commission_particulier': 8.0,
                             'commission_hotel': 12.0, 'commission_fondateur': 5.0, 'commission_transfert': 15.0}
        assert d['frais_menage']['villa'] == 15000

    def test_b9_traveller_fee_from_6_to_7_percent(self, admin, client_for, make_user, make_hebergement, api_client):
        voyageur = client_for(make_user())
        avant = _reserver(voyageur, make_hebergement(price_per_night=25000))
        reponse = admin.put(TARIFS, {'taux': {'frais_voyageur': 7}}, format='json')
        assert reponse.status_code == 200 and reponse.data['taux']['frais_voyageur'] == 7.0

        # New bookings and every displayed rate follow; a booking already made keeps its amounts
        apres = _reserver(voyageur, make_hebergement(price_per_night=25000))
        assert (avant.frais_service, apres.frais_service) == (3000, 3500)
        assert api_client.get('/api/v1/paiements/config/').data['frais_voyageur'] == 0.07
        avant.refresh_from_db()
        assert avant.frais_service == 3000
        journal = ActivityEntryModel.objects.get(action='tarifs_modifies')
        assert (journal.details['avant']['frais_voyageur'], journal.details['apres']['frais_voyageur']) == (6.0, 7.0)

    def test_commissions_and_cleaning_fee(self, admin, client_for, make_user, make_hebergement):
        admin.put(TARIFS, {'taux': {'commission_particulier': 9}, 'frais_menage': {'villa': 20000}}, format='json')
        resa = _reserver(client_for(make_user()), make_hebergement(type='villa', price_per_night=25000))
        assert (resa.commission_hote, resa.frais_menage) == (4500, 20000)
        assert FraisMenageModel.objects.get(type_logement='villa').montant == 20000

    @pytest.mark.parametrize('corps', [
        {'taux': {'frais_voyageur': 31}}, {'taux': {'frais_voyageur': -1}}, {'taux': {'commission_hotel': 'douze'}},
        {'taux': {'frais_reduits': 7}}, {'frais_menage': {'studio': -5}}, {'frais_menage': {'studio': '5000'}},
    ])
    def test_wrong_values_refused(self, admin, corps):
        assert admin.put(TARIFS, corps, format='json').status_code == 400
        assert ReglagesTarifsModel.actuels().frais_voyageur == Decimal('0.06')

    def test_admins_only(self, client_for, make_user):
        assert client_for(make_user(role='agent')).get(TARIFS).status_code == 403
        assert client_for(make_user(role='hote')).put(TARIFS, {'taux': {'frais_voyageur': 1}}, format='json').status_code == 403

    def test_transfers_follow(self, admin):
        from apps.transferts import tarifs as transferts

        admin.put(TARIFS, {'taux': {'commission_transfert': 20}}, format='json')
        assert transferts.commission_chauffeur() == Decimal('0.2')


class TestContrats:
    def test_templates_use_the_rates_in_force(self, admin):
        corps = ModeleContratModel.objects.get(type='hote').corps
        assert '{{ tarifs.commission_hote }} du prix des nuits' in corps and '8 % du prix des nuits' not in corps
        assert 'frais de ménage éventuels' not in corps and '{{ tarifs.frais_menage }}' in corps
        assert '{{ tarifs.commission_hotel }}' in ModeleContratModel.objects.get(type='hotel').corps

        admin.put(TARIFS, {'taux': {'commission_particulier': 9, 'frais_voyageur': 6.5}}, format='json')
        valeurs = contrats.contexte('hote', {'nom': 'Ama', 'email': 'ama@example.com', 'telephone': '', 'details': ''})
        texte = contrats.rendre(corps, valeurs)
        assert 'Commission de KWA-BA : 9 % du prix des nuits' in texte
        assert 'Frais de service du client (6,5 %, 3 % en Pack Séjour' in texte
        assert 'villa 15 000 F CFA' in texte and "aucuns frais pour chambre d'hôtel" in texte


class TestFinances:
    def test_period_money(self, admin, make_hebergement, make_user):
        hote_logement = make_hebergement(price_per_night=25000)
        resa = ReservationModel.objects.create(
            hebergement_id=hote_logement.id, guest_id=make_user().pk, check_in=timezone.localdate(),
            check_out=timezone.localdate() + timedelta(days=2), total_price=53000, status='confirmed',
            prix_nuits=50000, frais_service=3000, commission_hote=4000, frais_menage=0)
        paiement = PaiementModel.objects.create(reservation_id=resa.id, montant=53000, prestataire='fedapay', statut='reussi')
        RemboursementModel.objects.create(reservation_id=resa.id, paiement=paiement, montant=3000, motif='Geste commercial',
                                          statut='envoye', envoye_le=timezone.now())
        VersementModel.objects.create(reservation_id=resa.id, hote_id=hote_logement.host_id, montant_brut=50000,
                                      commission=4000, montant=46000, date_prevue=timezone.now() + timedelta(days=1))

        d = admin.get(FINANCES).data
        t = d['totaux']
        assert (t['encaisse'], t['nb_paiements'], t['rembourse'], t['verse'], t['du_partenaires'], t['revenu_kwaba']) == \
            (53000, 1, 3000, 0, 46000, 7000)
        assert d['par_produit'] == {'reservation': 53000}
        aujourd_hui = next(j for j in d['jours'] if j['date'] == timezone.localdate())
        assert (aujourd_hui['encaisse'], aujourd_hui['rembourse'], aujourd_hui['solde']) == (53000, 3000, 50000)

        csv = admin.get(f'{FINANCES}csv/').content.decode('utf-8-sig')
        assert csv.splitlines()[0].startswith('Date;Mouvement') and 'Encaissement;Séjour' in csv and ';-46000;4000;Planifié' in csv
        pdf = admin.get(f'{FINANCES}pdf/')
        assert pdf['Content-Type'] == 'application/pdf' and pdf.content.startswith(b'%PDF')
        assert ActivityEntryModel.objects.filter(action='finances_exportees').count() == 2

    def test_period_checked(self, admin):
        assert admin.get(FINANCES, {'debut': '2026-11-10', 'fin': '2026-11-01'}).status_code == 400
        assert admin.get(FINANCES, {'debut': '2025-01-01', 'fin': '2026-11-01'}).status_code == 400
        assert admin.get(f'{FINANCES}xlsx/').status_code == 404

    def test_admins_only(self, client_for, make_user):
        assert client_for(make_user(role='agent')).get(FINANCES).status_code == 403
