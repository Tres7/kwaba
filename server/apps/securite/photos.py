"""Validation and normalisation of the uploaded photos (listings, back-office)."""
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024        # 10 Mo
MAX_SOURCE_PIXELS = 40_000_000             # safeguard against "decompression bombs"
MAX_DIMENSION = 2000                       # longest side after resizing
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
JPEG_QUALITY = 82


class InvalidPhoto(ValueError):
    pass


def normalize_photo(uploaded_file) -> tuple[ContentFile, int, int]:
    """Checks the file then returns a resized, oriented JPEG without metadata (EXIF/GPS)."""
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise InvalidPhoto("La photo dépasse 10 Mo.")

    try:
        with Image.open(uploaded_file) as probe:
            fmt = probe.format
            width, height = probe.size
            probe.verify()  # detects truncated or corrupted files
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise InvalidPhoto("Ce fichier n'est pas une image valide.")

    if fmt not in ALLOWED_FORMATS:
        raise InvalidPhoto("Formats acceptés : JPEG, PNG ou WebP.")
    if width * height > MAX_SOURCE_PIXELS:
        raise InvalidPhoto("Image trop grande (40 mégapixels maximum).")
    if min(width, height) < 400:
        raise InvalidPhoto("Image trop petite : 400 pixels minimum de côté.")

    # verify() makes the image unusable: it is opened again to process it
    uploaded_file.seek(0)
    with Image.open(uploaded_file) as img:
        img = ImageOps.exif_transpose(img)      # applies the phone's rotation
        if img.mode != 'RGB':
            background = Image.new('RGB', img.size, (255, 255, 255))
            rgba = img.convert('RGBA')
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

        buffer = BytesIO()
        # No exif parameter: the metadata (GPS position, device) is not copied
        img.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
        return ContentFile(buffer.getvalue()), img.width, img.height
