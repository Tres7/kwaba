"""Spelling and grammar checker of the listings: LanguageTool, in a container on the internal network of the server.

The text never leaves Kwa-Ba's servers. LanguageTool unreachable, too slow or in error: `verifier` returns None, the
forms work as before without underlined mistakes.

Positions (`debut`, `longueur`) are counted in UTF-16 code units, like LanguageTool (Java) and the browser
(JavaScript): an emoji counts for 2, and the client can use the positions as they are.
"""
import logging
import re
import time
import unicodedata

import requests
from django.conf import settings

from . import lexique

logger = logging.getLogger('apps.correcteur')

LONGUEUR_MAX = 5000
# Language of the site → LanguageTool code. British spelling: the English of West Africa (Ghana, Nigeria)
LANGUES = {'fr': 'fr', 'en': 'en-GB'}
MAX_REMPLACEMENTS = 4
# LanguageTool down (connection refused), or too slow several times in a row: it is left alone for this long
# (seconds), so the forms do not wait for it on every key. A single slow answer (a description full of new place
# names: their spelling suggestions take time) is not a breakdown, and LanguageTool keeps the result for next time.
PAUSE_APRES_ECHEC = 60
ECHECS_AVANT_PAUSE = 3

# Filtered here and not sent to LanguageTool (disabledRules): it keeps one set of loaded rules per combination of
# settings, and the one kept loaded by its health check (deploy/vps/compose.yml) is the set without settings.
# Rules that report what a host cannot fix from a phone keyboard, or that are not mistakes in a listing
REGLES_ECARTEES = (
    'FRENCH_WHITESPACE',        # narrow no-break space before « : ; ! ? »
    'FRENCH_WHITESPACE_STRICT',
    'APOS_TYP',                 # typographic apostrophe ’ instead of '
    'TYPOGRAPHIC_QUOTES',
    'EN_QUOTES',
    'DASH_RULE',
)

# Style advice (« 5 » to write in letters, repetitions…) is not a mistake: a listing is not an essay
CATEGORIES_ECARTEES = ('STYLE',)

_pause_jusqua = 0.0
_echecs = 0

# Words that only French (or only English) uses: language of each line of the text
_MOTS_FR = frozenset(
    'le la les l de des du d et un une est sont pour avec dans au aux sur ce cette ces qui que qu où très vous votre '
    'vos nous notre nos il elle ils elles chambre chambres salle cuisine maison plage près proche situé située '
    'quartier pas par mais aussi tout tous'.split()
)
_MOTS_EN = frozenset(
    'the and with is are for of to our your you we this that these room rooms bedroom bedrooms bathroom kitchen '
    'house beach near close located from has have will be by but also all'.split()
)
_LIGNE = re.compile(r'[^\n]+')
_MOT = re.compile(r"[^\W\d_]+")


class _Indisponible(Exception):
    def __init__(self, message: str, panne: bool):
        super().__init__(message)
        # Connection refused or impossible: LanguageTool is not there, no need to try again at once
        self.panne = panne


def langue_de(texte: str) -> str | None:
    """'fr' or 'en' from the common words of the text; None when they do not tell."""
    mots = [m.casefold() for m in _MOT.findall(texte)]
    fr = sum(m in _MOTS_FR for m in mots)
    en = sum(m in _MOTS_EN for m in mots)
    if fr == en:
        return None
    return 'fr' if fr > en else 'en'


def segments(texte: str, langue_site: str) -> list[tuple[int, int, str]]:
    """(start, end, language) of the parts of the text, in Python indexes: consecutive lines in the same language.

    A host may write the description in French then in English: each part is checked in its own language. A line that
    does not tell (« - Wifi ») takes the language of the line before it, the first ones the language of the first line
    that tells, otherwise the language of the site.
    """
    lignes = [(m.start(), m.end(), langue_de(m.group())) for m in _LIGNE.finditer(texte)]
    if not lignes:
        return []
    connue = next((langue for _, _, langue in lignes if langue), langue_site)
    resultat: list[list] = []
    for debut, fin, langue in lignes:
        connue = langue or connue
        if resultat and resultat[-1][2] == connue:
            resultat[-1][1] = fin
        else:
            resultat.append([debut, fin, connue])
    return [(debut, fin, langue) for debut, fin, langue in resultat]


def longueur_utf16(texte: str) -> int:
    return len(texte.encode('utf-16-le')) // 2


def extrait_utf16(texte: str, debut: int, longueur: int) -> str:
    return texte.encode('utf-16-le')[2 * debut:2 * (debut + longueur)].decode('utf-16-le', errors='replace')


def _verifier_segment(texte: str, langue: str) -> list[dict]:
    try:
        reponse = requests.post(
            f"{settings.CORRECTEUR['URL'].rstrip('/')}/v2/check",
            data={'text': texte, 'language': LANGUES[langue]},
            timeout=(2, settings.CORRECTEUR['DELAI']),
        )
        reponse.raise_for_status()
        return reponse.json().get('matches', [])
    except (requests.RequestException, ValueError) as exc:
        raise _Indisponible(str(exc), panne=isinstance(exc, requests.ConnectionError)) from exc


def _distance(a: str, b: str) -> int:
    """Number of letters to add, remove or change to go from `a` to `b` (Levenshtein)."""
    precedente = list(range(len(b) + 1))
    for i, lettre in enumerate(a, 1):
        courante = [i]
        for j, autre in enumerate(b, 1):
            courante.append(min(precedente[j] + 1, courante[j - 1] + 1, precedente[j - 1] + (lettre != autre)))
        precedente = courante
    return precedente[-1]


def classer_suggestions(extrait: str, remplacements: list[str]) -> list[str]:
    """Spelling corrections closest to what was typed first, accents left aside: for « Deriere », LanguageTool puts
    « D'arrière » before « Derrière ». A correction that adds an apostrophe, a space or a hyphen comes after the others.
    Equal ones keep the order of LanguageTool (most frequent word first)."""
    ajouts = {"'", '’', ' ', '-'} - set(extrait)

    def squelette(mot: str) -> str:
        # Without accents, but with its capitals: « mason » stays closer to « maison » than to the name « Mason »
        return ''.join(c for c in unicodedata.normalize('NFD', mot) if not unicodedata.combining(c))

    cle = squelette(extrait)
    return sorted(remplacements, key=lambda r: (any(c in ajouts for c in r), _distance(squelette(r), cle)))


def _faute(texte: str, decalage: int, match: dict) -> dict | None:
    regle = match.get('rule') or {}
    if (regle.get('issueType') == 'style' or regle.get('id') in REGLES_ECARTEES
            or (regle.get('category') or {}).get('id') in CATEGORIES_ECARTEES):
        return None
    debut, longueur = int(match['offset']), int(match['length'])
    extrait = extrait_utf16(texte, debut, longueur)
    orthographe = regle.get('issueType') == 'misspelling'
    remplacements = [r['value'] for r in match.get('replacements') or [] if isinstance(r.get('value'), str)]
    if orthographe:
        if lexique.connu(extrait):
            return None
        remplacements = classer_suggestions(extrait, remplacements)
        proche = lexique.suggestion(extrait)
        if proche:
            remplacements = [proche, *[r for r in remplacements if r != proche]]
    return {
        'debut': decalage + debut,
        'longueur': longueur,
        'extrait': extrait,
        'type': 'orthographe' if orthographe else 'grammaire',
        'message': str(match.get('message') or ''),
        'remplacements': remplacements[:MAX_REMPLACEMENTS],
        'regle': str(regle.get('id') or ''),
    }


def verifier(texte: str, langue_site: str = 'fr') -> list[dict] | None:
    """Mistakes of `texte`, in the order of the text; None when LanguageTool cannot answer."""
    global _pause_jusqua, _echecs
    if not settings.CORRECTEUR['URL'] or time.monotonic() < _pause_jusqua:
        return None
    langue_site = langue_site if langue_site in LANGUES else 'fr'
    fautes = []
    try:
        for debut, fin, langue in segments(texte, langue_site):
            morceau = texte[debut:fin]
            if not morceau.strip():
                continue
            decalage = longueur_utf16(texte[:debut])
            for match in _verifier_segment(morceau, langue):
                faute = _faute(morceau, decalage, match)
                if faute:
                    fautes.append(faute)
    except _Indisponible as exc:
        _echecs += 1
        if exc.panne or _echecs >= ECHECS_AVANT_PAUSE:
            _pause_jusqua = time.monotonic() + PAUSE_APRES_ECHEC
            _echecs = 0
            logger.warning('LanguageTool injoignable, correcteur en pause %s s : %s', PAUSE_APRES_ECHEC, exc)
        else:
            logger.info('LanguageTool sans réponse (%s/%s) : %s', _echecs, ECHECS_AVANT_PAUSE, exc)
        return None
    _echecs = 0
    return fautes


def reprendre() -> None:
    """Ends the pause after a failure and forgets the failures (tests)."""
    global _pause_jusqua, _echecs
    _pause_jusqua, _echecs = 0.0, 0
