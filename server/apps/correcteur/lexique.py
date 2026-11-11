"""Words that are correct on Kwa-Ba but unknown to LanguageTool: Togolese place names, local words, brands.

Two sources: lexique.txt (fixed list) and the place names already in the database (cities and districts of the
listings, places of the experiences), read again every few minutes. From the database, only the words that start with
a capital letter are taken: a typo in a district typed by a host must not become a correct word.
"""
import re
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

FICHIER = Path(__file__).with_name('lexique.txt')
# The place names of the database are read again after this delay (seconds)
DUREE_LIEUX = 600

_MOT = re.compile(r"[^\W\d_]+")
_lieux: tuple[float, dict[str, str]] = (0.0, {})


def sans_accents(mot: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', mot) if not unicodedata.combining(c)).casefold()


def _ajouter(formes: dict[str, str], texte: str, majuscule_seulement: bool = False) -> None:
    """Adds each word of `texte`, keyed by its lower-case form; the value is the word as written (suggestion)."""
    for mot in _MOT.findall(texte):
        if majuscule_seulement and not mot[0].isupper():
            continue
        formes.setdefault(mot.casefold(), mot)


@lru_cache(maxsize=1)
def _fixes() -> dict[str, str]:
    formes: dict[str, str] = {}
    for ligne in FICHIER.read_text(encoding='utf-8').splitlines():
        ligne = ligne.split('#', 1)[0].strip()
        if ligne:
            _ajouter(formes, ligne)
    return formes


def _lieux_en_base() -> dict[str, str]:
    global _lieux
    if time.monotonic() < _lieux[0]:
        return _lieux[1]
    from apps.experiences.models import ExperienceModel
    from apps.hebergements.models import HebergementModel

    formes: dict[str, str] = {}
    for colonne in ('city', 'location'):
        for valeur in HebergementModel.objects.values_list(colonne, flat=True).distinct():
            _ajouter(formes, valeur or '', majuscule_seulement=True)
    for ville, nom in ExperienceModel.objects.values_list('ville', 'nom').distinct():
        _ajouter(formes, f'{ville} {nom}', majuscule_seulement=True)
    _lieux = (time.monotonic() + DUREE_LIEUX, formes)
    return formes


def oublier_lieux() -> None:
    """The next check reads the place names of the database again (tests)."""
    global _lieux
    _lieux = (0.0, {})


def _formes() -> dict[str, str]:
    return {**_lieux_en_base(), **_fixes()}


def connu(extrait: str) -> bool:
    """True when every word of `extrait` is in the lexicon (case does not matter)."""
    mots = _MOT.findall(extrait)
    formes = _formes()
    return bool(mots) and all(m.casefold() in formes for m in mots)


def suggestion(extrait: str) -> str | None:
    """Word of the lexicon written without its accents (« Kpalime » → « Kpalimé »), or None."""
    if not _MOT.fullmatch(extrait):
        return None
    cle = sans_accents(extrait)
    for forme in _formes().values():
        if sans_accents(forme) == cle and forme != extrait:
            return forme
    return None
