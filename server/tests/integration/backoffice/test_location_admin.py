"""Back-office: car hire management."""
from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from apps.locations.models import (
    CategorieVehiculeModel, LieuRemiseModel, LocationModel, PartenaireLocationModel, PhotoVehiculeModel,
)
from apps.securite.models import JournalAuditModel
from apps.transferts.models import ChauffeurModel

B = '/api/v1/admin/location/'


@pytest.fixture
def admin(make_user, client_for):
    return client_for(make_user(role='admin'))


@pytest.fixture(autouse=True)
def stockage(tmp_path, monkeypatch):
    monkeypatch.setattr(PhotoVehiculeModel._meta.get_field('image'), 'storage', FileSystemStorage(location=tmp_path))


@pytest.fixture
def lieu():
    return LieuRemiseModel.objects.create(nom='Aéroport de Lomé', ville='Lomé', fuseau='Africa/Lome')


@pytest.fixture
def berline():
    c = CategorieVehiculeModel.objects.get(nom='Berline')
    c.prix_jour, c.actif = 38000, True
    c.save()
    return c


@pytest.fixture
def location(make_user, berline, lieu):
    debut = timezone.now() + timedelta(days=5)
    return LocationModel.objects.create(
        voyageur=make_user(), categorie=berline, formule='avec_chauffeur', lieu_prise=lieu, lieu_retour=lieu,
        debut=debut, fin=debut + timedelta(days=3), passagers=2, telephone='+22890000000', precisions='Lomé - Kpalimé',
        jours=3, prix_jour=38000, frais_lieux=0, prix_chauffeur=21000, prix=135000, commission=17100,
        part_kwaba_chauffeur=3000, statut='confirmee',
    )


def _loueur(berline, lieu, **extra):
    p = PartenaireLocationModel.objects.create(nom='Lomé Auto', contact='Yao', telephone='+22890112233',
                                               pays_versement='TG', operateur_versement='togocel', numero_versement='90112233', **extra)
    p.categories.add(berline)
    p.lieux.add(lieu)
    return p


def test_reserve_aux_admins(make_user, client_for):
    assert client_for(make_user(role='agent')).get(B + 'categories/').status_code == 403


def test_regles_creees_puis_modifiees(admin):
    assert admin.get(B + 'regles/').data is None
    regles = {'commission_pourcent': '15', 'delai_min_jours': 2, 'duree_max_jours': 30, 'annulation_gratuite_heures': 48,
              'conditions': '23 ans minimum.'}
    assert admin.put(B + 'regles/', regles, format='json').status_code == 200
    assert admin.put(B + 'regles/', {**regles, 'delai_min_jours': 3}, format='json').data['delai_min_jours'] == 3
    assert JournalAuditModel.objects.filter(action='backoffice_modification', details__objet='regles_location').count() == 2


def _photo(nom='voiture.png'):
    tampon = BytesIO()
    Image.new('RGB', (900, 600), (20, 120, 200)).save(tampon, format='PNG')
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type='image/png')


def test_vehicule_prix_caution_et_activation(admin, lieu):
    citadine = CategorieVehiculeModel.objects.get(nom='Citadine')
    url = f'{B}categories/{citadine.id}/'
    proprietaire = _loueur(citadine, lieu)
    # No activation without a price nor an owner
    assert admin.patch(url, {'actif': True}, format='json').status_code == 400
    assert admin.patch(url, {'prix_jour': 25000, 'actif': True}, format='json').status_code == 400
    reponse = admin.patch(url, {'prix_jour': 25000, 'proprietaire': proprietaire.id, 'caution_jours': 2, 'actif': True}, format='json')
    assert reponse.data['actif'] is True and reponse.data['caution'] == 50000  # two days
    assert admin.patch(url, {'prix_jour': 80000}, format='json').data['caution'] == 100000  # plafond
    assert JournalAuditModel.objects.filter(action='backoffice_modification', details__objet='categorie_vehicule').exists()


def test_categorie_plusieurs_photos(admin, monkeypatch):
    citadine = CategorieVehiculeModel.objects.get(nom='Citadine')
    url = f'{B}categories/{citadine.id}/photos/'
    ids = []
    for i in range(3):
        reponse = admin.post(url, {'image': _photo(f'voiture{i}.png')}, format='multipart')
        assert reponse.status_code == 201 and len(reponse.data) == i + 1
        assert all(p['url'].endswith('.jpg') for p in reponse.data)
        ids.append(reponse.data[-1]['id'])
    assert [p['id'] for p in admin.get(f'{B}categories/{citadine.id}/').data['photos']] == ids
    assert admin.post(url, {'image': SimpleUploadedFile('x.txt', b'pas une image')}, format='multipart').status_code == 400

    # The third one becomes the main photo, then the first one is removed
    assert [p['id'] for p in admin.patch(f'{url}{ids[2]}/', {'principale': True}, format='json').data] == [ids[2], ids[0], ids[1]]
    assert [p['id'] for p in admin.delete(f'{url}{ids[0]}/').data] == [ids[2], ids[1]]
    assert admin.delete(f'{url}{ids[0]}/').status_code == 404

    # The public catalogue shows all the photos, the main one first (also in "image")
    citadine.prix_jour, citadine.actif = 25000, True
    citadine.save()
    from apps.locations.models import ParametresLocationModel
    ParametresLocationModel.objects.create(commission_pourcent=15, delai_min_jours=2, duree_max_jours=30, annulation_gratuite_heures=48)
    LieuRemiseModel.objects.create(nom='Aéroport de Lomé', ville='Lomé', fuseau='Africa/Lome')
    publique = next(c for c in admin.get('/api/v1/locations/catalogue/').data['categories'] if c['id'] == citadine.id)
    assert len(publique['photos']) == 2 and publique['image'] == publique['photos'][0]

    # Limit per category
    monkeypatch.setattr(PhotoVehiculeModel, 'MAX_PAR_CATEGORIE', 2)
    assert admin.post(url, {'image': _photo()}, format='multipart').status_code == 400
    assert JournalAuditModel.objects.filter(details__objet='categorie_vehicule', details__champs=['photos']).count() == 5


def test_lieu_et_loueur(admin, berline):
    lieu = admin.post(B + 'lieux/', {'nom': 'Aéroport de Cotonou', 'ville': 'Cotonou', 'fuseau': 'Africa/Porto-Novo'},
                      format='json')
    assert lieu.status_code == 201
    loueur = admin.post(B + 'loueurs/', {
        'nom': 'Cotonou Cars', 'contact': 'Ayaba', 'telephone': '+22997000000', 'categories': [berline.id],
        'lieux': [lieu.data['id']], 'pays_versement': 'BJ', 'operateur_versement': 'mtn_open', 'numero_versement': '0197000000',
    }, format='json')
    assert loueur.status_code == 201, loueur.data
    mauvais = admin.patch(f"{B}loueurs/{loueur.data['id']}/", {'operateur_versement': 'togocel'}, format='json')
    assert mauvais.status_code == 400
    assert admin.get(B + 'loueurs/').data[0]['nom'] == 'Cotonou Cars'
    assert JournalAuditModel.objects.filter(action='backoffice_creation', details__objet='loueur').exists()


def test_attribuer_proprietaire_et_chauffeur(admin, location, berline, lieu):
    bon = _loueur(berline, lieu)
    autre = _loueur(berline, lieu, email='')
    CategorieVehiculeModel.objects.filter(pk=berline.pk).update(proprietaire=bon)
    chauffeur = ChauffeurModel.objects.create(prenom='Komlan', nom='Ade', telephone='+22890998877', categorie='berline',
                                              vehicule='-', immatriculation='-', pays_versement='TG',
                                              operateur_versement='togocel', numero_versement='90998877', excellence=True)
    # The vehicle has an owner: only they are offered
    choix = admin.get(f'{B}locations/{location.id}/loueurs/', {'chauffeurs': 1}).data
    assert [p['id'] for p in choix['partenaires']] == [bon.id]
    assert choix['chauffeurs'] == [{'id': chauffeur.id, 'nom': 'Komlan Ade', 'telephone': '+22890998877', 'excellence': True, 'demande': False}]

    url = f'{B}locations/{location.id}/attribuer/'
    assert admin.post(url, {'partenaire': autre.id, 'chauffeur': chauffeur.id}, format='json').status_code == 400
    # Option with a driver: partner driver required
    assert admin.post(url, {'partenaire': bon.id, 'vehicule': 'Toyota Corolla grise'}, format='json').status_code == 400
    reponse = admin.post(url, {'partenaire': bon.id, 'chauffeur': chauffeur.id, 'vehicule': 'Toyota Corolla grise',
                               'immatriculation': 'TG 1234 AB'}, format='json')
    assert reponse.status_code == 200, reponse.data
    assert reponse.data['statut'] == 'partenaire_assigne' and reponse.data['partenaire']['nom'] == 'Lomé Auto'
    # Excellence driver: Kwa-Ba keeps 500 FCFA per day instead of 1,000
    assert (reponse.data['chauffeur_partenaire']['nom'], reponse.data['part_kwaba_chauffeur']) == ('Komlan Ade', 1500)


def test_proprietaire_fondateur(admin, lieu):
    jour = timezone.localdate()
    reponse = admin.post(B + 'loueurs/', {
        'nom': 'Ama Location', 'contact': 'Ama', 'telephone': '+22890000001', 'lieux': [lieu.id],
        'fondateur_debut': jour.isoformat(), 'pays_versement': 'TG', 'operateur_versement': 'togocel',
        'numero_versement': '90000001',
    }, format='json')
    assert reponse.status_code == 400  # start without end
    reponse = admin.post(B + 'loueurs/', {
        'nom': 'Ama Location', 'contact': 'Ama', 'telephone': '+22890000001', 'lieux': [lieu.id],
        'fondateur_debut': jour.isoformat(), 'fondateur_fin': (jour + timedelta(days=180)).isoformat(),
        'pays_versement': 'TG', 'operateur_versement': 'togocel', 'numero_versement': '90000001',
    }, format='json')
    assert reponse.status_code == 201, reponse.data


def test_liste_et_annulation(admin, location):
    assert admin.get(B + 'locations/', {'statut': 'confirmee'}).data['count'] == 1
    assert admin.post(f'{B}locations/{location.id}/annuler/', {}, format='json').status_code == 400
    reponse = admin.post(f'{B}locations/{location.id}/annuler/', {'motif': 'Aucun loueur disponible'}, format='json')
    assert reponse.status_code == 200 and reponse.data['statut'] == 'annulee'
