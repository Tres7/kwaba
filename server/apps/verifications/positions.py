"""Position of a listing read from what a field agent pastes: coordinates written down, a Google Maps link, or a location
shared in WhatsApp (which gives a Google Maps link too).

Short links (maps.app.goo.gl) do not contain the position: their redirection is followed, on these short-link hosts
only, and the address it leads to is read without being opened. No other site is ever requested.
"""
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests

HOTES_COURTS = frozenset({'maps.app.goo.gl', 'goo.gl'})
HOTE_GOOGLE = re.compile(r'^(?:www\.|maps\.)?google\.(?:com|[a-z]{2}|com?\.[a-z]{2})$')
REDIRECTIONS = frozenset({301, 302, 303, 307, 308})
SAUTS_MAX = 4
DELAI_S = 5
# Fewer decimals than this: the point could be more than 100 m away from the house
DECIMALES_MIN = 4

COPIER_COORDONNEES = "dans Google Maps, touchez le logement puis copiez les coordonnées affichées (6.13…, 1.22…)."

_URL = re.compile(r'https?://[^\s<>"]+', re.IGNORECASE)
# Marker of a place (data=…!3d<lat>!4d<lng>): the exact point, better than the centre of the view (@lat,lng)
_LIEU = re.compile(r'!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)')
_VUE = re.compile(r'@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)')
_CHEMIN = re.compile(r'/maps/(?:search|place|dir)/(?:[^/]*/)?\+?(-?\d+(?:\.\d+)?),\s*\+?(-?\d+(?:\.\d+)?)')
_PAIRE = re.compile(r'^\s*(?:loc:)?\s*(-?\d+(?:\.\d+)?)\s*,\s*\+?\s*(-?\d+(?:\.\d+)?)\s*$')
PARAMETRES = ('q', 'query', 'll', 'center', 'daddr', 'destination', 'sll')
_DECIMAL = re.compile(r'(?<!\d)-?\d{1,3}[.,]\d+')
# 6°07'54.8"N 1°13'22.1"E (as Google Maps shows it); O for "ouest"
_DMS = re.compile(r'(\d{1,3})\s*°\s*(\d{1,2})\s*[\'′’]\s*(\d{1,2}(?:[.,]\d+)?)\s*(?:"|″|”|\'\')?\s*([NSEWO])', re.IGNORECASE)
_PLUS_CODE = re.compile(r'\b[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}\b', re.IGNORECASE)


class PositionIllisible(Exception):
    pass


def lire(texte: str) -> tuple[Decimal, Decimal]:
    """(latitude, longitude) of what was pasted; PositionIllisible with a message for the agent otherwise."""
    texte = (texte or '').strip()[:2000]
    if not texte:
        raise PositionIllisible("Collez un lien Google Maps, une position WhatsApp ou des coordonnées.")
    url = _URL.search(texte)
    latitude, longitude = _depuis_url(url.group(0)) if url else _depuis_texte(texte)
    return _valider(latitude, longitude)


def _depuis_texte(texte: str) -> tuple[str, str]:
    dms = _DMS.findall(texte)
    if len(dms) == 2:
        return _depuis_dms(dms)
    nombres = _DECIMAL.findall(texte)
    if len(nombres) == 2:
        if any(len(re.split(r'[.,]', n)[1]) < DECIMALES_MIN for n in nombres):
            raise PositionIllisible(f"Coordonnées trop imprécises : il faut au moins {DECIMALES_MIN} chiffres après la "
                                    f"virgule (environ 10 m). Sinon, {COPIER_COORDONNEES}")
        return nombres[0].replace(',', '.'), nombres[1].replace(',', '.')
    if _PLUS_CODE.search(texte):
        raise PositionIllisible(f"Les plus codes (4Q6J+…) ne sont pas lus : {COPIER_COORDONNEES}")
    raise PositionIllisible(f"Position illisible : collez une latitude et une longitude, ou un lien Google Maps. "
                            f"Pour les obtenir, {COPIER_COORDONNEES}")


def _depuis_dms(dms: list[tuple]) -> tuple[str, str]:
    valeurs = {}
    for degres, minutes, secondes, sens in dms:
        sens = sens.upper()
        valeur = Decimal(degres) + Decimal(minutes) / 60 + Decimal(secondes.replace(',', '.')) / 3600
        axe = 'latitude' if sens in 'NS' else 'longitude'
        valeurs[axe] = -valeur if sens in 'SWO' else valeur
    if set(valeurs) != {'latitude', 'longitude'}:
        raise PositionIllisible("Il faut une latitude (N ou S) et une longitude (E ou O).")
    return str(valeurs['latitude']), str(valeurs['longitude'])


def _depuis_url(url: str) -> tuple[str, str]:
    url = _suivre(url)
    parties = urlsplit(url)
    hote = (parties.hostname or '').lower()
    if hote == 'consent.google.com':  # cookie consent page in front of Google Maps: the map's address is kept in it
        suite = parse_qs(parties.query).get('continue', [''])[0]
        return _depuis_url(suite) if suite and urlsplit(suite).hostname != 'consent.google.com' else _sans_coordonnees()
    if not HOTE_GOOGLE.match(hote):
        raise PositionIllisible(f"Lien non reconnu : seuls les liens Google Maps sont lus. Sinon, {COPIER_COORDONNEES}")
    lien = unquote(url)
    if trouve := _LIEU.search(lien):
        return trouve.groups()
    for cle in PARAMETRES:
        for valeur in parse_qs(parties.query).get(cle, []):
            if trouve := _PAIRE.match(valeur):
                return trouve.groups()
    for motif in (_CHEMIN, _VUE):
        if trouve := motif.search(lien):
            return trouve.groups()
    return _sans_coordonnees()


def _sans_coordonnees():
    raise PositionIllisible(f"Ce lien ne contient pas la position (lien vers une adresse ou un nom de lieu) : "
                            f"{COPIER_COORDONNEES}")


def _suivre(url: str) -> str:
    """Address a short link leads to. Only the short-link hosts are requested (https, no port nor account in the
    address), at most SAUTS_MAX times; what they redirect to is returned without being opened."""
    for _ in range(SAUTS_MAX):
        parties = urlsplit(url)
        if (parties.hostname or '').lower() not in HOTES_COURTS:
            return url
        if parties.scheme != 'https' or parties.port or parties.username or parties.password:
            raise PositionIllisible("Lien Google Maps invalide : copiez-le à nouveau depuis le bouton Partager.")
        try:
            reponse = requests.get(url, allow_redirects=False, timeout=DELAI_S, stream=True,
                                   headers={'User-Agent': 'Kwa-Ba'})
            reponse.close()
        except requests.RequestException:
            raise PositionIllisible(f"Google Maps ne répond pas. Réessayez, ou {COPIER_COORDONNEES}")
        suite = reponse.headers.get('Location')
        if reponse.status_code not in REDIRECTIONS or not suite:
            raise PositionIllisible(f"Ce lien court ne mène à aucune carte (expiré ?) : {COPIER_COORDONNEES}")
        url = urljoin(url, suite)
    raise PositionIllisible(f"Ce lien fait trop de détours : {COPIER_COORDONNEES}")


def _valider(latitude, longitude) -> tuple[Decimal, Decimal]:
    try:
        latitude = Decimal(str(latitude)).quantize(Decimal('0.000001'))
        longitude = Decimal(str(longitude)).quantize(Decimal('0.000001'))
    except InvalidOperation:
        raise PositionIllisible("Position illisible.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or (latitude == 0 and longitude == 0):
        raise PositionIllisible("Ces coordonnées n'existent pas : la latitude vient d'abord (6.13… au Togo), "
                                "puis la longitude (1.22…).")
    return latitude, longitude
