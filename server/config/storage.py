"""Storage of uploaded files (photos, avatars) on Cloudflare R2, through its S3-compatible API."""
from collections.abc import Mapping


def r2_storage(env: Mapping[str, str]) -> dict | None:
    """R2 storage backend if R2_BUCKET is set, otherwise None (local disk)."""
    if not env.get('R2_BUCKET'):
        return None
    return {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': env['R2_BUCKET'],
            'endpoint_url': env['R2_ENDPOINT_URL'],          # https://<compte>.r2.cloudflarestorage.com
            'access_key': env['R2_ACCESS_KEY_ID'],
            'secret_key': env['R2_SECRET_ACCESS_KEY'],
            # Public domain of the bucket (without https://): photo URLs are saved in the listings,
            # they must stay valid (no signed URL that expires)
            'custom_domain': env['R2_PUBLIC_DOMAIN'],
            'querystring_auth': False,
            'region_name': 'auto',
            'signature_version': 's3v4',
            'default_acl': None,      # R2 does not support ACLs
            'file_overwrite': False,
        },
    }


def r2_storage_prive(env: Mapping[str, str]) -> dict | None:
    """Private documents (hosts' identity documents, visit photos) in an R2 bucket without a public domain.

    Never a public URL: files are only read by the API, after checking the role (apps.verifications).
    None if R2_PRIVE_BUCKET is not set (local disk, folder not served by the web server).
    """
    if not env.get('R2_PRIVE_BUCKET'):
        return None
    return {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': env['R2_PRIVE_BUCKET'],
            'endpoint_url': env['R2_ENDPOINT_URL'],
            'access_key': env['R2_ACCESS_KEY_ID'],
            'secret_key': env['R2_SECRET_ACCESS_KEY'],
            'querystring_auth': True,     # no public URL
            'region_name': 'auto',
            'signature_version': 's3v4',
            'default_acl': None,
            'file_overwrite': False,
        },
    }
