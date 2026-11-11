import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from django.conf import settings

BLOCK, WARN, ALLOW = 'block', 'warn', 'allow'
LEVELS = (ALLOW, WARN, BLOCK)
CATEGORIES = ('insult', 'hate', 'threat', 'harassment')

MODE_OFF, MODE_OBSERVE, MODE_ENFORCE = 'off', 'observe', 'enforce'
MODES = (MODE_OFF, MODE_OBSERVE, MODE_ENFORCE)

EXCERPT_LENGTH = 120
LEXICONS_DIR = Path(__file__).parent / 'moderation_lexicons'

_LEET = str.maketrans({'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b',
                       '@': 'a', '$': 's', '!': 'i', '|': 'i', '€': 'e'})
_TOKEN = re.compile(r'[a-z0-9@$!|€]+')
_REPEATS = re.compile(r'(.)\1+')
_BOUNDARY_BEFORE = r'(?<![a-z0-9])'
_BOUNDARY_AFTER = r'(?![a-z0-9])'
_MAX_FILLERS = 2


@dataclass(frozen=True)
class ModerationResult:
    level: str = ALLOW
    categories: tuple[str, ...] = field(default_factory=tuple)

    @property
    def flagged(self) -> bool:
        return self.level != ALLOW


def mode() -> str:
    value = (settings.MODERATION.get('MODE') or '').strip().lower()
    return value if value in MODES else MODE_OBSERVE


def excerpt(text: str) -> str:
    text = ' '.join((text or '').split())
    return text if len(text) <= EXCERPT_LENGTH else text[:EXCERPT_LENGTH - 1].rstrip() + '…'


def _token(raw: str) -> str:
    raw = raw.rstrip('!|')
    if any(c.isalpha() for c in raw):
        raw = raw.translate(_LEET)
    return re.sub(r'[^a-z0-9]', '', raw)


def _join_spelled_letters(tokens: list[str]) -> list[str]:
    joined, run = [], []
    for token in tokens + ['']:
        if len(token) == 1 and token.isalpha():
            run.append(token)
            continue
        joined.extend([''.join(run)] if len(run) >= 3 else run)
        run = []
        if token:
            joined.append(token)
    return joined


def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(c for c in text if not unicodedata.combining(c) and unicodedata.category(c) != 'Cf').lower()
    tokens = [t for t in (_token(raw) for raw in _TOKEN.findall(text)) if t]
    return ' '.join(_REPEATS.sub(r'\1', t) for t in _join_spelled_letters(tokens))


def _word_pattern(word: str) -> str:
    wildcard = word.endswith('*')
    stem = normalize(word.rstrip('*'))
    return re.escape(stem).replace(r'\ ', ' ') + (r'[a-z0-9]*' if wildcard else '')


def _term_pattern(term: str) -> str:
    parts = []
    for word in term.split():
        if word.startswith('(') and word.endswith(')'):
            choices = word[1:-1].split('|')
            optional = '' in choices
            alternatives = '|'.join(_word_pattern(c.replace('_', ' ')) for c in choices if c)
            parts.append((f'(?:{alternatives})', optional))
        else:
            parts.append((_word_pattern(word), False))
    pattern = ''
    for index, (part, optional) in enumerate(parts):
        separator = ' ' if index else ''
        pattern += f'(?:{separator}{part})?' if optional else f'{separator}{part}'
    return pattern


def _alternatives(phrases) -> str:
    return '|'.join(sorted({_term_pattern(p) for p in phrases}, key=len, reverse=True))


@dataclass(frozen=True)
class _Rule:
    category: str
    level: str
    regex: re.Pattern


@dataclass(frozen=True)
class _Lexicon:
    rules: tuple[_Rule, ...]
    exceptions: re.Pattern | None


def _load_files(directory: Path) -> list[dict]:
    return [json.loads(path.read_text(encoding='utf-8')) for path in sorted(directory.glob('*.json'))]


@lru_cache(maxsize=4)
def lexicon(directory: Path = LEXICONS_DIR) -> _Lexicon:
    files = _load_files(directory)
    targets = _alternatives(t for f in files for t in f.get('targets', []))
    suffixes = _alternatives(t for f in files for t in f.get('suffix_targets', []))
    fillers = _alternatives(t for f in files for t in f.get('fillers', []))
    exceptions = [e for f in files for e in f.get('exceptions', [])]
    rules = []
    for data in files:
        for entry in data.get('entries', []):
            if entry['category'] not in CATEGORIES or entry['level'] not in (WARN, BLOCK):
                raise ValueError(f"Invalid moderation entry: {entry['category']} / {entry['level']}")
            terms = _alternatives(entry['terms'])
            if entry.get('targeted'):
                body = f'(?:{targets})(?: (?:{fillers})){{0,{_MAX_FILLERS}}} (?:{terms})'
                if suffixes:
                    body = f'(?:{body}|(?:{terms}) (?:{suffixes}))'
            else:
                body = f'(?:{terms})'
            rules.append(_Rule(entry['category'], entry['level'],
                               re.compile(_BOUNDARY_BEFORE + body + _BOUNDARY_AFTER)))
    exceptions_regex = (re.compile(_BOUNDARY_BEFORE + f'(?:{_alternatives(exceptions)})' + _BOUNDARY_AFTER)
                        if exceptions else None)
    return _Lexicon(tuple(rules), exceptions_regex)


def analyze(text: str, directory: Path = LEXICONS_DIR) -> ModerationResult:
    data = lexicon(directory)
    normalized = normalize(text)
    if data.exceptions:
        normalized = data.exceptions.sub(' | ', normalized)
    matched = [rule for rule in data.rules if rule.regex.search(normalized)]
    if not matched:
        return ModerationResult()
    level = max((rule.level for rule in matched), key=LEVELS.index)
    return ModerationResult(level, tuple(sorted({rule.category for rule in matched}, key=CATEGORIES.index)))
