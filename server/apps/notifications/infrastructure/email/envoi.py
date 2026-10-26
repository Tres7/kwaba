from email.mime.image import MIMEImage
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from .html import CID_LOGO, page_html

LOGO = Path(__file__).with_name('kwaba-logo-email.png')


@lru_cache(maxsize=1)
def _logo() -> bytes:
    return LOGO.read_bytes()


def send_mail(subject: str, message: str, from_email: str, recipient_list: list[str],
              pieces_jointes: list[tuple[str, bytes, str]] | None = None) -> int:
    """Like django.core.mail.send_mail, as text and HTML in the Kwa-Ba colours.

    - the site's reply-to address (EMAIL_REPLY_TO): emails leave from a "noreply" address,
      a reply from the recipient reaches the contact mailbox;
    - HTML version with the logo attached to the email (Content-ID), displayed without a remote image;
    - `pieces_jointes`: (name, content, MIME type), for example the booking voucher as a PDF.
    """
    # One email per recipient: nobody sees the other recipients' addresses (staff alerts go to several admins and
    # field agents). Duplicates are dropped, and all emails share a single SMTP connection.
    uniques: dict[str, str] = {}
    for adresse in recipient_list:
        if adresse.strip():
            uniques.setdefault(adresse.strip().lower(), adresse.strip())
    destinataires = list(uniques.values())
    if not destinataires:
        return 0
    html = page_html(message, subject)
    emails = [_email(subject, message, html, from_email, adresse, pieces_jointes) for adresse in destinataires]
    return get_connection().send_messages(emails)


def _email(subject: str, message: str, html: str, from_email: str, destinataire: str,
           pieces_jointes: list[tuple[str, bytes, str]] | None) -> EmailMultiAlternatives:
    reply_to = [settings.EMAIL_REPLY_TO] if settings.EMAIL_REPLY_TO else None
    email = EmailMultiAlternatives(subject, message, from_email, [destinataire], reply_to=reply_to)
    email.attach_alternative(html, 'text/html')
    email.mixed_subtype = 'related'
    logo = MIMEImage(_logo(), 'png')
    logo.add_header('Content-ID', f'<{CID_LOGO}>')
    logo.add_header('Content-Disposition', 'inline', filename='kwaba.png')
    email.attach(logo)
    for nom, contenu, type_mime in pieces_jointes or []:
        email.attach(nom, contenu, type_mime)
    return email
