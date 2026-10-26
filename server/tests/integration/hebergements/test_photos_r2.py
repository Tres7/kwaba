from io import BytesIO

import boto3
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from moto import mock_aws
from PIL import Image

from apps.hebergements.models import HebergementPhotoModel
from config.storage import r2_storage

PHOTOS = '/api/v1/hebergements/photos/'
R2_ENV = {
    'R2_BUCKET': 'kwaba-photos',
    'R2_ENDPOINT_URL': 'https://compte-test.r2.cloudflarestorage.com',
    'R2_ACCESS_KEY_ID': 'test-key',
    'R2_SECRET_ACCESS_KEY': 'test-secret',
    'R2_PUBLIC_DOMAIN': 'photos.kwaba.example',
}


@pytest.fixture
def r2_bucket(settings, monkeypatch):
    """Fake R2 (moto) at the R2 address, with the production storage configuration."""
    monkeypatch.setenv('MOTO_S3_CUSTOM_ENDPOINTS', R2_ENV['R2_ENDPOINT_URL'])
    with mock_aws():
        client = boto3.client('s3', endpoint_url=R2_ENV['R2_ENDPOINT_URL'], region_name='us-east-1',
                              aws_access_key_id='test-key', aws_secret_access_key='test-secret')
        client.create_bucket(Bucket=R2_ENV['R2_BUCKET'])
        settings.STORAGES = {**settings.STORAGES, 'default': r2_storage(R2_ENV)}
        yield client


def _jpeg():
    buffer = BytesIO()
    Image.new('RGB', (800, 600), (30, 120, 200)).save(buffer, format='JPEG')
    return SimpleUploadedFile('vacances.jpg', buffer.getvalue(), content_type='image/jpeg')


def test_no_r2_variables_means_local_disk():
    assert r2_storage({}) is None


def test_photo_uploaded_to_r2_with_stable_public_url(r2_bucket, client_for, make_user):
    host = make_user(role='hote')
    response = client_for(host).post(PHOTOS, {'file': _jpeg()}, format='multipart')

    assert response.status_code == 201
    key = f'hebergements/{host.id}/{response.data["id"]}.jpg'
    # Public URL, without a signature that would expire: it is saved as is in the listing
    assert response.data['url'] == f'https://photos.kwaba.example/{key}'
    stored = r2_bucket.head_object(Bucket='kwaba-photos', Key=key)
    assert stored['ContentType'] == 'image/jpeg'


def test_photo_deleted_from_r2(r2_bucket, client_for, make_user):
    host = make_user(role='hote')
    photo_id = client_for(host).post(PHOTOS, {'file': _jpeg()}, format='multipart').data['id']
    key = HebergementPhotoModel.objects.get(pk=photo_id).image.name

    assert client_for(host).delete(f'{PHOTOS}{photo_id}/').status_code == 204
    assert r2_bucket.list_objects_v2(Bucket='kwaba-photos').get('KeyCount') == 0
    assert key.startswith(f'hebergements/{host.id}/')


def test_photo_url_under_the_site_domain(r2_bucket, client_for, make_user, settings):
    # Production: nginx serves the bucket under https://kwa-ba.com/photos/ (R2_PUBLIC_DOMAIN may contain a path)
    settings.STORAGES = {**settings.STORAGES, 'default': r2_storage({**R2_ENV, 'R2_PUBLIC_DOMAIN': 'kwa-ba.com/photos'})}
    host = make_user(role='hote')
    response = client_for(host).post(PHOTOS, {'file': _jpeg()}, format='multipart')

    assert response.status_code == 201
    assert response.data['url'] == f'https://kwa-ba.com/photos/hebergements/{host.id}/{response.data["id"]}.jpg'

