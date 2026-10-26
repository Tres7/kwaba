"""HTML version of the emails, built from their text version.

Templates stay as text (readable everywhere); their layout follows simple conventions,
converted here into HTML in the Kwa-Ba colours:
- a single line of 4 to 8 digits (indented)            → highlighted code;
- a block of indented lines ("Key: value")             → details card;
- "Label: https://…" or a link alone                   → button (the label comes from the line or the previous one);
- "L'équipe Kwa-Ba" and the closing line before it     → signature.
The logo is attached to the email (Content-ID): it shows without loading an image from the Internet.
"""
import html
import re

from django.conf import settings

CID_LOGO = 'logo-kwaba'
VERT, ORANGE, ORANGE_FONCE, CREME, TEXTE, GRIS = '#0E4D47', '#F59E0B', '#B45309', '#F8F6F2', '#1F2937', '#5F6B6C'

_URL = re.compile(r'(https?://[^\s<>"]+)')
_CODE = re.compile(r'^\s{2,}(\d{4,8})\s*$')
_BOUTON = re.compile(r'^(?P<libelle>[^:]{3,80}?)\s*:\s*(?P<url>https?://\S+)\s*$')
_URL_SEULE = re.compile(r'^\s*(https?://\S+)\s*$')


def _liens(texte_echappe: str) -> str:
    return _URL.sub(lambda m: f'<a href="{m.group(1)}" style="color:{VERT};font-weight:600">{m.group(1)}</a>', texte_echappe)


def _bouton(libelle: str, url: str) -> str:
    libelle = libelle.strip().rstrip(':').strip() or 'Ouvrir'
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0"><tr><td style="border-radius:12px;background:{VERT}">'
            f'<a href="{html.escape(url)}" style="display:inline-block;padding:13px 26px;font-family:Arial,Helvetica,sans-serif;font-size:15px;'
            f'font-weight:700;color:#FFFFFF;text-decoration:none;border-radius:12px">{html.escape(libelle[:1].upper() + libelle[1:])}</a></td></tr></table>')


def _paragraphe(lignes: list[str]) -> str:
    contenu = '<br>'.join(_liens(html.escape(ligne.strip())) for ligne in lignes)
    return f'<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:{TEXTE}">{contenu}</p>'


def _details(lignes: list[str]) -> str:
    rangees = []
    for ligne in lignes:
        cle, sep, valeur = ligne.strip().partition(' : ')
        if sep:
            rangees.append(f'<tr><td style="padding:6px 14px 6px 0;font-size:13px;color:{GRIS};white-space:nowrap;vertical-align:top">{html.escape(cle)}</td>'
                           f'<td style="padding:6px 0;font-size:14px;color:{TEXTE};font-weight:600">{_liens(html.escape(valeur))}</td></tr>')
        else:
            rangees.append(f'<tr><td colspan="2" style="padding:6px 0;font-size:14px;color:{TEXTE}">{_liens(html.escape(ligne.strip()))}</td></tr>')
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:4px 0 18px;background:{CREME};'
            f'border-left:4px solid {ORANGE};border-radius:10px"><tr><td style="padding:14px 18px"><table role="presentation" cellpadding="0" cellspacing="0">'
            + ''.join(rangees) + '</table></td></tr></table>')


def _code(code: str) -> str:
    return (f'<div style="margin:6px 0 20px;padding:18px;text-align:center;background:{CREME};border:2px dashed {ORANGE};border-radius:14px;'
            f'font-family:\'Courier New\',monospace;font-size:34px;font-weight:700;letter-spacing:10px;color:{VERT}">{html.escape(code)}</div>')


def corps_html(texte: str) -> str:
    """Converts the text of an email into HTML blocks."""
    blocs = re.split(r'\n\s*\n', texte.strip().replace('\r', ''))
    sortie = []
    for i, bloc in enumerate(blocs):
        lignes = [ligne.rstrip() for ligne in bloc.split('\n') if ligne.strip()]
        if not lignes:
            continue
        code = _CODE.match(bloc) if len(lignes) == 1 else None
        if code:
            sortie.append(_code(code.group(1)))
            continue
        if all(ligne.startswith('  ') for ligne in lignes):
            sortie.append(_details(lignes))
            continue
        if i == len(blocs) - 1 and lignes[-1].strip().startswith("L'équipe"):
            sortie.append(f'<p style="margin:24px 0 0;font-size:15px;line-height:1.6;color:{TEXTE}">'
                          + '<br>'.join(html.escape(ligne.strip()) for ligne in lignes[:-1])
                          + ('<br>' if len(lignes) > 1 else '')
                          + f'<strong style="color:{VERT}">{html.escape(lignes[-1].strip())}</strong></p>')
            continue
        # Text lines, with buttons for the action links
        tampon = []
        for j, ligne in enumerate(lignes):
            seule = _URL_SEULE.match(ligne)
            bouton = _BOUTON.match(ligne.strip())
            if seule:
                libelle = tampon.pop() if tampon and tampon[-1].strip().endswith(':') else 'Ouvrir'
                if tampon:
                    sortie.append(_paragraphe(tampon))
                    tampon = []
                sortie.append(_bouton(libelle, seule.group(1)))
            elif bouton and not bouton.group('libelle').startswith(('http', ' ')):
                if tampon:
                    sortie.append(_paragraphe(tampon))
                    tampon = []
                sortie.append(_bouton(bouton.group('libelle'), bouton.group('url')))
            else:
                tampon.append(ligne)
        if tampon:
            sortie.append(_paragraphe(tampon))
    return '\n'.join(sortie)


def page_html(texte: str, sujet: str) -> str:
    """Full email: header with the logo, content, footer."""
    contact = getattr(settings, 'EMAIL_REPLY_TO', '') or getattr(settings, 'ASSISTANCE_CONTACT', '')
    pied_contact = (f'Une question ? Répondez à cet email ou écrivez à '
                    f'<a href="mailto:{html.escape(contact)}" style="color:{VERT}">{html.escape(contact)}</a>.<br>') if contact else ''
    apercu = html.escape(re.sub(r'\s+', ' ', texte.strip())[:110])
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>{html.escape(sujet)}</title></head>
<body style="margin:0;padding:0;background:{CREME};font-family:Arial,Helvetica,sans-serif;-webkit-text-size-adjust:100%">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{apercu}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CREME}"><tr><td align="center" style="padding:28px 12px">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#FFFFFF;border-radius:18px;overflow:hidden;border:1px solid #ECE7DD">
    <tr><td align="center" style="padding:26px 24px 18px;border-bottom:1px solid #F0ECE4">
      <img src="cid:{CID_LOGO}" width="200" height="50" alt="KWA-BA" style="display:block;border:0;outline:none;font-family:Arial,sans-serif;font-size:26px;font-weight:800;color:{VERT}">
      <div style="margin-top:8px;font-size:12px;letter-spacing:3px;text-transform:uppercase;color:{GRIS}">L’Afrique vous accueille</div>
    </td></tr>
    <tr><td style="height:4px;background:{ORANGE};background-image:linear-gradient(90deg,{VERT},{ORANGE},{ORANGE_FONCE})"></td></tr>
    <tr><td style="padding:30px 32px 26px">
{corps_html(texte)}
    </td></tr>
  </table>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px"><tr><td align="center" style="padding:18px 16px;font-size:12px;line-height:1.6;color:{GRIS}">
    {pied_contact}<strong style="color:{VERT}">Kwa-Ba</strong> · Hébergements, transferts et expériences en Afrique de l'Ouest
  </td></tr></table>
</td></tr></table>
</body></html>'''
