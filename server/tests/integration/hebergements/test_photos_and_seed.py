from io import BytesIO, StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from apps.hebergements.models import HebergementModel, HebergementPhotoModel
from apps.users.infrastructure.persistence.models import UserModel

PHOTOS = '/api/v1/hebergements/photos/'


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _jpeg():
    buffer = BytesIO()
    Image.new('RGB', (800, 600), (30, 120, 200)).save(buffer, format='JPEG')
    return SimpleUploadedFile('vacances.jpg', buffer.getvalue(), content_type='image/jpeg')


class TestPhotoUpload:
    def test_host_uploads_photo_stored_under_owner_folder(self, client_for, make_user, media_root):
        host = make_user(role='hote')
        response = client_for(host).post(PHOTOS, {'file': _jpeg()}, format='multipart')

        assert response.status_code == 201
        photo = HebergementPhotoModel.objects.get(pk=response.data['id'])
        assert photo.image.name == f'hebergements/{host.id}/{photo.id}.jpg'
        assert (media_root / photo.image.name).exists()
        assert (response.data['width'], response.data['height']) == (800, 600)

    def test_guest_forbidden(self, client_for, make_user):
        assert client_for(make_user()).post(PHOTOS, {'file': _jpeg()}, format='multipart').status_code == 403

    def test_missing_file(self, client_for, make_user):
        assert client_for(make_user(role='hote')).post(PHOTOS, {}, format='multipart').status_code == 400

    def test_invalid_file_message(self, client_for, make_user):
        bogus = SimpleUploadedFile('photo.jpg', b'pas une image', content_type='image/jpeg')
        response = client_for(make_user(role='hote')).post(PHOTOS, {'file': bogus}, format='multipart')
        assert response.status_code == 400
        assert response.data['file']

    def test_delete_by_owner_removes_file(self, client_for, make_user, media_root):
        host = make_user(role='hote')
        photo_id = client_for(host).post(PHOTOS, {'file': _jpeg()}, format='multipart').data['id']
        path = media_root / HebergementPhotoModel.objects.get(pk=photo_id).image.name

        assert client_for(make_user(role='hote')).delete(f'{PHOTOS}{photo_id}/').status_code == 404
        assert client_for(host).delete(f'{PHOTOS}{photo_id}/').status_code == 204
        assert not path.exists()


def test_seed_demo_is_idempotent(api_client, monkeypatch):
    monkeypatch.setenv('DEMO_HOST_EMAIL', 'hote.demo@kwa-ba.com')
    monkeypatch.setenv('DEMO_HOST_PASSWORD', 'Kwa-Ba2026!')

    call_command('seed_demo', stdout=StringIO())
    call_command('seed_demo', stdout=StringIO())

    host = UserModel.objects.get(email='hote.demo@kwa-ba.com')
    assert HebergementModel.objects.filter(host_id=host.pk).count() == 12
    response = api_client.post('/api/v1/auth/login/', {'email': host.email, 'password': 'Kwa-Ba2026!'},
                               format='json')
    assert response.status_code == 200
