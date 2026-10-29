from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.securite.photos import MAX_UPLOAD_BYTES, InvalidPhoto, normalize_photo

EXIF_ORIENTATION = 0x0112
ROTATED_90 = 6


def _upload(width=800, height=600, fmt='JPEG', mode='RGB', exif=None, color=(200, 120, 40)):
    buffer = BytesIO()
    image = Image.new(mode, (width, height), color if mode != '1' else 1)
    options = {'exif': exif} if exif is not None else {}
    image.save(buffer, format=fmt, **options)
    return SimpleUploadedFile(f'photo.{fmt.lower()}', buffer.getvalue())


def _open(content):
    return Image.open(BytesIO(content.read()))


@pytest.mark.parametrize('fmt', ['JPEG', 'PNG', 'WEBP'])
def test_accepted_formats_become_jpeg(fmt):
    content, width, height = normalize_photo(_upload(fmt=fmt))
    assert _open(content).format == 'JPEG'
    assert (width, height) == (800, 600)


@pytest.mark.parametrize('fmt', ['GIF', 'BMP'])
def test_other_formats_rejected(fmt):
    with pytest.raises(InvalidPhoto, match='Formats'):
        normalize_photo(_upload(fmt=fmt))


def test_not_an_image():
    with pytest.raises(InvalidPhoto):
        normalize_photo(SimpleUploadedFile('photo.jpg', b'ceci est un texte'))


def test_truncated_file():
    data = _upload(fmt='PNG').read()
    with pytest.raises(InvalidPhoto):
        normalize_photo(SimpleUploadedFile('photo.png', data[: len(data) // 2]))


def test_file_over_10_megabytes():
    with pytest.raises(InvalidPhoto, match='10 Mo'):
        normalize_photo(SimpleUploadedFile('photo.jpg', b'\0' * (MAX_UPLOAD_BYTES + 1)))


def test_over_40_megapixels():
    with pytest.raises(InvalidPhoto, match='40 mégapixels'):
        normalize_photo(_upload(width=7000, height=6000, fmt='PNG', mode='1'))


def test_side_under_400_pixels():
    with pytest.raises(InvalidPhoto, match='400'):
        normalize_photo(_upload(width=1000, height=399))


def test_large_image_resized_to_2000_pixels():
    _, width, height = normalize_photo(_upload(width=4000, height=3000))
    assert (width, height) == (2000, 1500)


def test_transparent_png_flattened_on_white():
    content, _, _ = normalize_photo(_upload(fmt='PNG', mode='RGBA', color=(0, 0, 0, 0)))
    red, green, blue = _open(content).getpixel((10, 10))
    assert min(red, green, blue) >= 250


def test_exif_rotation_applied_and_metadata_stripped():
    exif = Image.Exif()
    exif[EXIF_ORIENTATION] = ROTATED_90
    content, width, height = normalize_photo(_upload(width=800, height=600, exif=exif.tobytes()))

    assert (width, height) == (600, 800)
    assert dict(_open(content).getexif()) == {}
