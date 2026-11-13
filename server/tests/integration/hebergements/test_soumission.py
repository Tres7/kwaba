"""Sending a wizard draft: every condition is checked by the server, whatever the browser says."""
import uuid

import pytest

from apps.contrats.models import PreinscriptionModel
from apps.hebergements.models import BrouillonAnnonceModel, HebergementModel, HebergementPhotoModel
from apps.paiements.models import ProfilVersementModel
from apps.activity.models import ActivityEntryModel
from apps.users.infrastructure.persistence.models import UserModel
from apps.verifications.models import PieceIdentiteModel

BROUILLONS = '/api/v1/hebergements/brouillons/'
HEBERGEMENTS = '/api/v1/hebergements/'


def _photos(hote, nombre=5):
    urls = []
    for _ in range(nombre):
        photo = HebergementPhotoModel.objects.create(
            owner_id=hote.pk, width=800, height=600, image=f'hebergements/{hote.pk}/x.jpg')
        urls.append(f'https://kwa-ba.test/photos/hebergements/{hote.pk}/{photo.pk}.jpg')
    return urls


def _donnees(urls, **extra):
    return {
        'name': 'Villa des cocotiers', 'type': 'villa', 'city': 'Lomé', 'location': 'Baguida',
        'latitude': 6.13, 'longitude': 1.22, 'price_per_night': 35000, 'max_guests': 4, 'point_repere': 'Derrière la pharmacie', 'salles_de_bain': 1, 'chambres': 2,
        'lits_doubles': 2, 'petit_dejeuner': 'inclus', 'amenities': ['wifi'], 'description': 'Une villa calme près de la plage.',
        'image_url': urls[0], 'images': urls, 'legendes_photos': {url: 'salon' for url in urls}, 'declarations': {'cameras': False, 'attestation': True}, **extra,
    }


@pytest.fixture(autouse=True)
def images_du_site(settings):
    settings.IMAGES_HOTES_AUTORISES = [*settings.IMAGES_HOTES_AUTORISES, 'kwa-ba.test']


@pytest.fixture
def candidat(make_user):
    return make_user(phone='+22890000001', candidature_hote='ouverte')


@pytest.fixture
def pret(candidat):
    """Everything done: only the sending is left."""
    PieceIdentiteModel.objects.create(hote_id=candidat.pk, type_piece='cni', statut='soumise')
    ProfilVersementModel.objects.create(hote_id=candidat.pk, pays='TG', operateur='togocel', numero='90000001', titulaire='Ama Koffi')
    return BrouillonAnnonceModel.objects.create(host_id=candidat.pk, donnees=_donnees(_photos(candidat)))


def _soumettre(client, brouillon):
    return client.post(f'{BROUILLONS}{brouillon.pk}/soumettre/')


class TestEnvoi:
    def test_creates_the_listing_and_deletes_the_draft(self, client_for, candidat, pret):
        reponse = _soumettre(client_for(candidat), pret)

        assert reponse.status_code == 201
        annonce = HebergementModel.objects.get()
        assert (annonce.host_id, annonce.statut_verification) == (candidat.pk, 'en_attente')
        assert annonce.attestation_le is not None
        assert annonce.declarations == {'cameras': False, 'attestation': True}
        assert not BrouillonAnnonceModel.objects.exists()
        assert HebergementPhotoModel.objects.filter(hebergement_id=annonce.pk).count() == 5

    def test_host_stays_a_candidate_until_an_agent_validates(self, client_for, candidat, pret):
        _soumettre(client_for(candidat), pret)
        candidat.refresh_from_db()
        assert candidat.role == 'voyageur'

    def test_second_click_creates_nothing_more(self, client_for, candidat, pret):
        client = client_for(candidat)
        _soumettre(client, pret)
        assert _soumettre(client, pret).status_code == 404
        assert HebergementModel.objects.count() == 1

    def test_someone_elses_draft(self, client_for, make_user, pret):
        assert _soumettre(client_for(make_user(role='hote')), pret).status_code == 404
        assert not HebergementModel.objects.exists()


class TestConditions:
    @pytest.mark.parametrize('condition', ['telephone', 'identite', 'versement', 'attestation', 'photos'])
    def test_refused_while_a_condition_is_missing(self, client_for, candidat, pret, condition):
        if condition == 'telephone':
            UserModel.objects.filter(pk=candidat.pk).update(phone=None)
            candidat.refresh_from_db()
        elif condition == 'identite':
            PieceIdentiteModel.objects.all().delete()
        elif condition == 'versement':
            ProfilVersementModel.objects.all().delete()
        elif condition == 'attestation':
            pret.donnees['declarations'] = {'attestation': False}
            pret.save()
        else:
            pret.donnees['images'] = pret.donnees['images'][:4]
            pret.save()

        reponse = _soumettre(client_for(candidat), pret)

        assert reponse.status_code == 400
        assert reponse.data['code'] == 'conditions'
        assert condition in reponse.data['bloquants']
        assert not HebergementModel.objects.exists()
        assert BrouillonAnnonceModel.objects.filter(pk=pret.pk).exists()

    def test_refused_identity_blocks(self, client_for, candidat, pret):
        PieceIdentiteModel.objects.update(statut='refusee')
        assert 'identite' in _soumettre(client_for(candidat), pret).data['bloquants']

    def test_photos_of_another_host_refused(self, client_for, make_user, candidat, pret):
        pret.donnees['images'] = _photos(make_user(role='hote'))
        pret.save()
        assert 'photos_du_compte' in _soumettre(client_for(candidat), pret).data['bloquants']

    def test_outside_image_refused(self, client_for, candidat, pret):
        pret.donnees['images'] = [*pret.donnees['images'][:4], 'https://images.unsplash.com/photo-1.jpg']
        pret.save()
        assert 'photos_du_compte' in _soumettre(client_for(candidat), pret).data['bloquants']

    def test_invented_photo_refused(self, client_for, candidat, pret):
        pret.donnees['images'] = [*pret.donnees['images'][:4], f'https://kwa-ba.test/photos/hebergements/{candidat.pk}/{uuid.uuid4()}.jpg']
        pret.save()
        assert 'photos_du_compte' in _soumettre(client_for(candidat), pret).data['bloquants']

    def test_preregistration_required_during_prelaunch(self, client_for, candidat, pret, settings):
        settings.PRELANCEMENT = True
        client = client_for(candidat)
        assert 'preinscription' in _soumettre(client, pret).data['bloquants']

        PreinscriptionModel.objects.create(hote_id=candidat.pk, version=1, langue='fr', empreinte_texte='x')
        assert _soumettre(client, pret).status_code == 201

    def test_contact_details_refused_and_reported(self, client_for, candidat, pret):
        pret.donnees['description'] = 'Appelez-moi au 90 00 00 01 pour réserver.'
        pret.save()

        reponse = _soumettre(client_for(candidat), pret)

        assert reponse.status_code == 400
        assert 'description' in reponse.data
        assert not HebergementModel.objects.exists()

    def test_refused_candidate(self, client_for, candidat, pret):
        UserModel.objects.filter(pk=candidat.pk).update(candidature_hote='refusee')
        candidat.refresh_from_db()
        assert _soumettre(client_for(candidat), pret).status_code == 403

    def test_conditions_shown_to_the_host(self, client_for, candidat, pret):
        ProfilVersementModel.objects.all().delete()

        reponse = client_for(candidat).get(f'{BROUILLONS}{pret.pk}/conditions/')

        assert reponse.status_code == 200
        assert reponse.data['telephone'] is True
        assert reponse.data['identite'] == 'soumise'
        assert reponse.data['bloquants'] == ['versement']

    def test_conditions_of_someone_elses_draft(self, client_for, make_user, pret):
        assert client_for(make_user(role='hote')).get(f'{BROUILLONS}{pret.pk}/conditions/').status_code == 404


class TestAncienneRoute:
    def test_closed_once_the_wizard_is_on(self, client_for, candidat, settings):
        settings.MODULES = {**settings.MODULES, 'assistant_hote': True}
        reponse = client_for(candidat).post(HEBERGEMENTS, _donnees(['https://kwa-ba.test/a.jpg']), format='json')
        assert (reponse.status_code, reponse.data['code']) == (403, 'assistant_requis')

    def test_still_open_to_administrators(self, client_for, make_user, settings):
        settings.MODULES = {**settings.MODULES, 'assistant_hote': True}
        admin = make_user(role='admin', phone='+22890000002')
        assert client_for(admin).post(HEBERGEMENTS, _donnees(['https://kwa-ba.test/a.jpg']), format='json').status_code == 201

    def test_unchanged_while_the_wizard_is_off(self, client_for, candidat):
        assert client_for(candidat).post(HEBERGEMENTS, _donnees(['https://kwa-ba.test/a.jpg']), format='json').status_code == 201


class TestDeclarations:
    def test_unknown_statement_refused_in_a_draft(self, client_for, candidat, pret):
        reponse = client_for(candidat).patch(f'{BROUILLONS}{pret.pk}/', {'donnees': {'declarations': {'armes': True}}}, format='json')
        assert 'declarations' in reponse.data['erreurs']

    def test_audit_trail_of_a_role_is_not_touched_by_the_sending(self, client_for, candidat, pret):
        _soumettre(client_for(candidat), pret)
        assert not ActivityEntryModel.objects.filter(action='role_modifie').exists()
