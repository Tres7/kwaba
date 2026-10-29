"""Back-office: Kwa-Ba Give (NGOs, projects, transfers with proof, donations)."""
from datetime import date, timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from apps.give.models import DonModel, OrganisationModel, ReversementModel
from apps.securite.models import JournalAuditModel

B = '/api/v1/admin/give/'


@pytest.fixture(autouse=True)
def medias(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def admin(make_user, client_for):
    return client_for(make_user(role='admin'))


def _image(nom='photo.png'):
    tampon = BytesIO()
    Image.new('RGB', (900, 600), (30, 140, 90)).save(tampon, format='PNG')
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type='image/png')


def _ong(**extra):
    return OrganisationModel.objects.create(
        nom='Écoles du Mono', slug='ecoles-du-mono', cause='education', pays='TG', ville='Aného', resume='Fournitures',
        description='Soutien scolaire.', numero_enregistrement='TG-2020-12', coordonnees_reversement='Flooz 90000000', **extra)


def test_reserve_aux_admins(make_user, client_for):
    assert client_for(make_user()).get(B + 'organisations/').status_code == 403


def test_creer_une_ong_puis_la_publier(admin):
    reponse = admin.post(B + 'organisations/', {
        'nom': 'Côtes vivantes', 'cause': 'environnement', 'pays': 'TG', 'ville': 'Lomé', 'resume': 'Plages propres',
        'description': 'Nettoyage des plages.', 'numero_enregistrement': 'TG-2021-77', 'image': _image(),
    }, format='multipart')
    assert reponse.status_code == 201, reponse.data
    assert reponse.data['slug'] == 'cotes-vivantes' and reponse.data['image'].endswith('.jpg')
    url = f"{B}organisations/{reponse.data['id']}/"
    # Publishing requires saying what was verified
    assert admin.patch(url, {'verifiee_le': '2026-10-01'}, format='json').status_code == 400
    publie = admin.patch(url, {'verifiee_le': '2026-10-01', 'verification': 'Récépissé et statuts vérifiés'}, format='json')
    assert publie.status_code == 200
    assert JournalAuditModel.objects.filter(details__objet='ong').count() == 2


def test_projets_d_une_ong(admin):
    ong = _ong()
    reponse = admin.post(f'{B}organisations/{ong.id}/projets/', {'titre': 'Rentrée 2026', 'cause': 'education',
                                                                 'resume': '300 kits', 'objectif': 1500000}, format='json')
    assert reponse.status_code == 201 and reponse.data['organisation'] == ong.id
    assert len(admin.get(f'{B}organisations/{ong.id}/projets/').data) == 1
    assert admin.patch(f"{B}projets/{reponse.data['id']}/", {'actif': False}, format='json').data['actif'] is False


def test_reversement_effectue_avec_preuve(admin, make_user):
    ong = _ong(verifiee_le=date(2026, 9, 1), verification='Vérifiée')
    mois_dernier = (timezone.localdate().replace(day=1) - timedelta(days=1)).replace(day=1)
    DonModel.objects.create(donateur_id=make_user().pk, organisation=ong, montant=2000, frais=0, total=2000, montant_ong=2000,
                            statut='paye', paye_le=timezone.make_aware(timezone.datetime.combine(mois_dernier, timezone.datetime.min.time())))
    assert admin.post(B + 'reversements/preparer/').data['dons'] == 1
    r = ReversementModel.objects.get(organisation=ong)
    liste = admin.get(B + 'reversements/', {'statut': 'a_effectuer'}).data
    assert liste['count'] == 1 and liste['results'][0]['coordonnees_reversement'] == 'Flooz 90000000'

    url = f'{B}reversements/{r.id}/effectuer/'
    assert admin.post(url, {'moyen': 'mobile_money', 'reference_operation': 'TX123'}, format='multipart').status_code == 400
    faux = SimpleUploadedFile('preuve.pdf', b'MZ pas un pdf', content_type='application/pdf')
    assert admin.post(url, {'moyen': 'mobile_money', 'reference_operation': 'TX123', 'justificatif': faux},
                      format='multipart').status_code == 400
    pdf = SimpleUploadedFile('preuve.pdf', b'%PDF-1.7\n%preuve\n', content_type='application/pdf')
    reponse = admin.post(url, {'moyen': 'mobile_money', 'reference_operation': 'TX123', 'justificatif': pdf,
                               'note': 'Fournitures achetées.'}, format='multipart')
    assert reponse.status_code == 200, reponse.data
    assert reponse.data['statut'] == 'effectue' and reponse.data['justificatif'].endswith('.pdf')
    assert admin.post(url, {'moyen': 'mobile_money', 'reference_operation': 'TX9', 'justificatif': _image()},
                      format='multipart').status_code == 400


def test_dons_en_lecture(admin, make_user):
    ong = _ong()
    DonModel.objects.create(donateur_id=make_user(email='awa@test.tg').pk, organisation=ong, montant=500, frais=15, total=515,
                            montant_ong=500, statut='paye', paye_le=timezone.now())
    assert admin.get(B + 'dons/', {'q': 'awa'}).data['count'] == 1
    assert admin.get(B + 'dons/', {'organisation': 'pas-un-uuid'}).status_code == 400
    assert admin.get(B + 'dons/', {'organisation': str(ong.id), 'statut': 'paye'}).data['count'] == 1
