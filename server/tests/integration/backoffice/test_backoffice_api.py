from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.avis.models import CRITERES, AvisModel
from apps.hebergements.models import HebergementModel
from apps.reservations.models import ReservationModel
from apps.securite.models import JournalAuditModel

ADMIN = '/api/v1/admin/'


@pytest.fixture
def admin(make_user):
    return make_user(role='admin')


@pytest.fixture
def api_admin(admin, client_for):
    return client_for(admin)


def _avis(reservation, note):
    return AvisModel.objects.create(
        reservation_id=reservation.id, hebergement_id=reservation.hebergement_id, auteur_id=reservation.guest.id,
        note=note, **{critere: note for critere in CRITERES}, commentaire='Commentaire de test assez long.',
    )


class TestAcces:
    @pytest.mark.parametrize('route', ['stats/', 'users/', 'hebergements/', 'reservations/', 'avis/'])
    def test_anonyme_refuse(self, api_client, route):
        assert api_client.get(ADMIN + route).status_code == 401

    @pytest.mark.parametrize('role', ['voyageur', 'hote', 'agent'])
    def test_autres_roles_refuses(self, make_user, client_for, role):
        reponse = client_for(make_user(role=role)).get(ADMIN + 'users/')
        assert reponse.status_code == 403
        assert reponse.data['detail'] == 'Accès réservé aux administrateurs.'


class TestStats:
    def test_compteurs_et_serie_de_30_jours(self, api_admin, make_user, make_hebergement, make_reservation):
        make_user(role='hote', is_active=False)
        logement = make_hebergement(price_per_night=10000)
        make_hebergement(statut_verification='en_attente')
        make_hebergement(is_available=False)
        make_hebergement(statut_verification='refusee')  # waits for the host, not for an agent
        confirmee = make_reservation(logement, status='confirmed')
        ReservationModel.objects.filter(pk=confirmee.pk).update(total_price=30000)
        make_reservation(logement, status='cancelled')
        ancienne = make_reservation(logement, status='confirmed')
        ReservationModel.objects.filter(pk=ancienne.pk).update(created_at=timezone.now() - timedelta(days=45), total_price=99999)
        _avis(confirmee, 4)
        _avis(ancienne, 5)

        d = api_admin.get(ADMIN + 'stats/').data

        assert d['utilisateurs']['desactives'] == 1
        assert d['annonces'] == {'total': 4, 'visibles': 1, 'verifiees': 2, 'en_attente': 1}
        assert d['reservations'] == {'confirmees_30j': 1, 'annulees_30j': 1, 'volume_30j': 30000}
        assert d['avis'] == {'total': 2, 'moyenne': 4.5}
        serie = d['reservations_par_jour']
        assert len(serie) == 30
        assert serie[-1] == {'date': timezone.localdate().isoformat(), 'nombre': 1, 'volume': 30000}
        assert sum(j['nombre'] for j in serie) == 1

    def test_sans_avis_moyenne_nulle(self, api_admin):
        assert api_admin.get(ADMIN + 'stats/').data['avis'] == {'total': 0, 'moyenne': None}


class TestUtilisateurs:
    def test_liste_filtres_et_pagination(self, api_admin, make_user, make_hebergement):
        hote = make_user(role='hote', first_name='Kossi', phone='+22890000001')
        make_hebergement(host=hote)
        make_user(role='voyageur', is_active=False)

        d = api_admin.get(ADMIN + 'users/', {'q': 'koss'}).data
        assert d['count'] == 1
        assert d['results'][0]['nb_annonces'] == 1
        assert api_admin.get(ADMIN + 'users/', {'q': '90000001'}).data['count'] == 1
        assert api_admin.get(ADMIN + 'users/', {'actif': 'false'}).data['count'] == 1
        assert api_admin.get(ADMIN + 'users/', {'role': 'admin'}).data['count'] == 1

        page = api_admin.get(ADMIN + 'users/', {'page_size': 2, 'page': 2}).data
        assert (page['page'], page['page_size'], page['count'], len(page['results'])) == (2, 2, 3, 1)
        assert api_admin.get(ADMIN + 'users/', {'page': 9}).data['results'] == []

    def test_changer_le_role(self, api_admin, make_user):
        cible = make_user()

        reponse = api_admin.patch(f'{ADMIN}users/{cible.id}/', {'role': 'agent'}, format='json')

        assert reponse.status_code == 200
        assert reponse.data['role'] == 'agent'
        entree = JournalAuditModel.objects.get(action='role_modifie')
        assert entree.details['apres'] == 'agent' and entree.details['cible_email'] == cible.email

    def test_role_invalide(self, api_admin, make_user):
        reponse = api_admin.patch(f'{ADMIN}users/{make_user().id}/', {'role': 'roi'}, format='json')
        assert reponse.status_code == 400

    def test_desactiver_ferme_les_sessions(self, api_admin, make_user):
        cible = make_user()
        RefreshToken.for_user(cible)

        reponse = api_admin.patch(f'{ADMIN}users/{cible.id}/', {'is_active': False}, format='json')

        assert reponse.status_code == 200 and reponse.data['is_active'] is False
        jeton = OutstandingToken.objects.get(user=cible)
        assert BlacklistedToken.objects.filter(token=jeton).exists()
        assert JournalAuditModel.objects.filter(action='compte_desactive').exists()

    def test_pas_sur_son_propre_compte(self, api_admin, admin):
        reponse = api_admin.patch(f'{ADMIN}users/{admin.id}/', {'is_active': False}, format='json')
        assert reponse.status_code == 403
        admin.refresh_from_db()
        assert admin.is_active

    def test_inconnu(self, api_admin):
        assert api_admin.patch(f'{ADMIN}users/00000000-0000-0000-0000-000000000000/', {'role': 'hote'}, format='json').status_code == 404


class TestAnnonces:
    def test_liste_et_filtres(self, api_admin, make_hebergement):
        make_hebergement(name='Villa Hibiscus', city='Assinie')
        make_hebergement(name='Studio', city='Lomé', statut_verification='en_attente', is_available=False)

        assert api_admin.get(ADMIN + 'hebergements/', {'q': 'hibis'}).data['count'] == 1
        assert api_admin.get(ADMIN + 'hebergements/', {'ville': 'lomé'}).data['count'] == 1
        assert api_admin.get(ADMIN + 'hebergements/', {'visible': 'false'}).data['count'] == 1
        attente = api_admin.get(ADMIN + 'hebergements/', {'verifie': 'false'}).data
        assert attente['count'] == 1
        assert attente['results'][0]['est_verifie'] is False

    def test_masquer_puis_valider(self, api_admin, make_hebergement):
        annonce = make_hebergement(statut_verification='en_attente')

        r = api_admin.patch(f'{ADMIN}hebergements/{annonce.id}/', {'is_available': False}, format='json')
        assert r.status_code == 200 and r.data['is_available'] is False

        r = api_admin.patch(f'{ADMIN}hebergements/{annonce.id}/', {'est_verifie': True}, format='json')
        assert r.data['est_verifie'] is True
        annonce.refresh_from_db()
        assert annonce.statut_verification == 'verifiee'
        assert JournalAuditModel.objects.filter(action='annonce_modifiee').count() == 2

    def test_retirer_la_validation_retire_du_site(self, api_admin, make_hebergement):
        annonce = make_hebergement()

        api_admin.patch(f'{ADMIN}hebergements/{annonce.id}/', {'est_verifie': False}, format='json')

        assert not HebergementModel.objects.publiees().filter(pk=annonce.pk).exists()

    def test_supprimer_exige_un_motif(self, api_admin, make_hebergement):
        annonce = make_hebergement()

        assert api_admin.delete(f'{ADMIN}hebergements/{annonce.id}/').status_code == 400
        assert api_admin.delete(f'{ADMIN}hebergements/{annonce.id}/?motif=Faux').status_code == 400

        reponse = api_admin.delete(f'{ADMIN}hebergements/{annonce.id}/?motif=Annonce frauduleuse')
        assert reponse.status_code == 204
        assert not HebergementModel.objects.filter(pk=annonce.pk).exists()
        assert HebergementModel.tous.filter(pk=annonce.pk).exists()
        assert JournalAuditModel.objects.get(action='annonce_supprimee').details['motif'] == 'Annonce frauduleuse'


class TestReservations:
    def test_liste_et_filtres(self, api_admin, make_hebergement, make_reservation, make_user):
        logement = make_hebergement(name='Suite Océan')
        voyageur = make_user(email='kofi@exemple.com')
        resa = make_reservation(logement, guest=voyageur, starts_in=10, nights=3)
        make_reservation(make_hebergement(name='Autre'), starts_in=40, status='cancelled')

        d = api_admin.get(ADMIN + 'reservations/', {'q': 'kofi'}).data
        assert d['count'] == 1
        element = d['results'][0]
        assert element['reference'] == resa.reference and element['nights'] == 3
        assert element['hebergement']['name'] == 'Suite Océan'
        assert api_admin.get(ADMIN + 'reservations/', {'q': resa.reference}).data['count'] == 1
        assert api_admin.get(ADMIN + 'reservations/', {'statut': 'cancelled'}).data['count'] == 1

        debut = timezone.localdate() + timedelta(days=12)
        periode = api_admin.get(ADMIN + 'reservations/', {'debut': debut.isoformat(), 'fin': (debut + timedelta(days=5)).isoformat()}).data
        assert [r['id'] for r in periode['results']] == [str(resa.id)]

    def test_annulation_meme_sejour_commence(self, api_admin, make_hebergement, make_reservation):
        resa = make_reservation(make_hebergement(), starts_in=-1, nights=4)

        assert api_admin.post(f'{ADMIN}reservations/{resa.id}/annuler/', {}, format='json').status_code == 400
        reponse = api_admin.post(f'{ADMIN}reservations/{resa.id}/annuler/', {'motif': 'Doublon signalé'}, format='json')

        assert reponse.status_code == 200 and reponse.data['status'] == 'cancelled'
        resa.refresh_from_db()
        assert resa.annule_par == 'plateforme'
        assert JournalAuditModel.objects.get(action='reservation_annulee').details['motif'] == 'Doublon signalé'

        deja = api_admin.post(f'{ADMIN}reservations/{resa.id}/annuler/', {'motif': 'Doublon signalé'}, format='json')
        assert deja.status_code == 400
        assert deja.data['detail'] == 'Cette réservation est déjà annulée.'


class TestAvis:
    def test_liste_et_suppression_recalcule_la_note(self, api_admin, make_hebergement, make_reservation):
        logement = make_hebergement()
        mauvais = _avis(make_reservation(logement, starts_in=-10), 1)
        _avis(make_reservation(logement, starts_in=-20), 5)

        assert api_admin.get(ADMIN + 'avis/', {'note': 1}).data['count'] == 1
        assert api_admin.get(ADMIN + 'avis/').data['count'] == 2

        reponse = api_admin.delete(f'{ADMIN}avis/{mauvais.id}/?motif=Propos injurieux')

        assert reponse.status_code == 204
        logement.refresh_from_db()
        assert (logement.rating, logement.review_count) == (5.0, 1)
        assert JournalAuditModel.objects.get(action='avis_supprime').details['note'] == 1
