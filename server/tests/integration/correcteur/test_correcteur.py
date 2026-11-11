"""Spelling checker of the listings: API, Kwa-Ba lexicon, LanguageTool unreachable. LanguageTool is simulated."""
import pytest
import requests

from apps.correcteur import lexique, services

VERIFIER = '/api/v1/correcteur/verifier/'


def _match(offset, length, issue='misspelling', regle='FR_SPELLING_RULE', remplacements=(), message='Faute de frappe',
           categorie='TYPOS'):
    return {'offset': offset, 'length': length, 'message': message, 'replacements': [{'value': r} for r in remplacements],
            'rule': {'id': regle, 'issueType': issue, 'category': {'id': categorie}}}


class FauxLanguageTool:
    """Answers with the matches given for each text; keeps the requests."""

    def __init__(self, reponses=None, erreur=None):
        self.reponses, self.erreur, self.requetes = reponses or {}, erreur, []

    def __call__(self, url, data, timeout):
        self.requetes.append({'url': url, **data})
        if self.erreur:
            raise self.erreur
        matches = self.reponses.get(data['text'], [])
        return type('Reponse', (), {'raise_for_status': lambda self: None, 'json': lambda self: {'matches': matches}})()


@pytest.fixture
def languagetool(settings, monkeypatch):
    settings.CORRECTEUR = {'URL': 'http://languagetool:8010', 'DELAI': 5}
    services.reprendre()
    lexique.oublier_lieux()

    def installer(**kwargs):
        faux = FauxLanguageTool(**kwargs)
        monkeypatch.setattr(services.requests, 'post', faux)
        return faux

    yield installer
    services.reprendre()
    lexique.oublier_lieux()


@pytest.fixture
def hote(make_user, client_for):
    return client_for(make_user(role='hote'))


def test_connexion_obligatoire(api_client, languagetool):
    faux = languagetool()
    assert api_client.post(VERIFIER, {'texte': 'Une mason'}, format='json').status_code == 401
    assert faux.requetes == []


def test_texte_attendu_et_longueur_maximale(hote, languagetool):
    languagetool()
    assert hote.post(VERIFIER, {'texte': 12}, format='json').status_code == 400
    assert hote.post(VERIFIER, {'texte': 'a' * (services.LONGUEUR_MAX + 1)}, format='json').status_code == 400


def test_fautes_avec_positions_et_corrections(hote, languagetool):
    texte = 'Une jolie mason avec piscine'
    faux = languagetool(reponses={texte: [
        _match(10, 5, remplacements=['maison', 'masson', 'macon', 'maçon', 'Mason']),
        _match(0, 3, issue='grammar', regle='ACCORD', message='Accord du nom.', remplacements=['Un']),
    ]})
    reponse = hote.post(VERIFIER, {'texte': texte, 'langue': 'fr'}, format='json')
    assert reponse.status_code == 200
    assert reponse.data['disponible'] is True
    orthographe, grammaire = reponse.data['fautes']
    assert orthographe == {'debut': 10, 'longueur': 5, 'extrait': 'mason', 'type': 'orthographe', 'message': 'Faute de frappe',
                           'remplacements': ['maison', 'masson', 'macon', 'maçon'], 'regle': 'FR_SPELLING_RULE'}
    assert grammaire['type'] == 'grammaire' and grammaire['remplacements'] == ['Un']
    requete, = faux.requetes
    # Only the text and its language: the rules kept loaded by the health check of the container are used
    assert requete == {'url': 'http://languagetool:8010/v2/check', 'text': texte, 'language': 'fr'}


def test_conseils_de_style_et_typographie_ecartes(hote, languagetool):
    texte = 'Maison de 3 chambres : salon'
    languagetool(reponses={texte: [
        # « 3 » to write in letters: style advice, not a mistake in a listing
        _match(10, 1, issue='style', regle='NOMBRES_EN_LETTRES_2', categorie='STYLE', remplacements=['trois']),
        # Narrow no-break space before « : »: nothing a host can type on a phone
        _match(20, 1, issue='typographical', regle='FRENCH_WHITESPACE', categorie='TYPOGRAPHY'),
        _match(23, 5, issue='style', regle='AUTRE_STYLE', categorie='REDUNDANCY'),
    ]})
    assert hote.post(VERIFIER, {'texte': texte}, format='json').data == {'disponible': True, 'fautes': []}


def test_noms_de_lieux_togolais_jamais_signales(hote, languagetool, make_hebergement):
    make_hebergement(city='Lomé', location='Akodésséwa marché')
    texte = 'Studio à Kodjoviakopé, près de Akodésséwa et du marché'
    languagetool(reponses={texte: [_match(9, 12), _match(31, 10)]})
    reponse = hote.post(VERIFIER, {'texte': texte, 'langue': 'fr'}, format='json')
    # Kodjoviakopé is in lexique.txt, Akodésséwa comes from the district of a listing
    assert reponse.data == {'disponible': True, 'fautes': []}


def test_mot_du_lexique_sans_accent_corrige(hote, languagetool):
    texte = 'Appartement a Kpalime'
    languagetool(reponses={texte: [_match(14, 7, remplacements=['Kpalm'])]})
    faute, = hote.post(VERIFIER, {'texte': texte}, format='json').data['fautes']
    assert faute['remplacements'] == ['Kpalimé', 'Kpalm']


def test_chaque_partie_dans_sa_langue(hote, languagetool):
    francais, anglais = 'Belle maison dans le quartier 🌴', 'Beautifull house near the beach'
    faux = languagetool(reponses={anglais: [_match(0, 10, regle='MORFOLOGIK_RULE_EN_GB', remplacements=['Beautiful'])]})
    reponse = hote.post(VERIFIER, {'texte': f'{francais}\n\n{anglais}', 'langue': 'fr'}, format='json')
    assert [(r['language'], r['text']) for r in faux.requetes] == [('fr', francais), ('en-GB', anglais)]
    faute, = reponse.data['fautes']
    # Position in the whole text, in UTF-16 units (the emoji counts for 2)
    assert faute['debut'] == len(francais) + 1 + 2 and faute['extrait'] == 'Beautifull'


def test_languagetool_injoignable(hote, languagetool):
    faux = languagetool(erreur=requests.ConnectionError('refus'))
    reponse = hote.post(VERIFIER, {'texte': 'Une mason'}, format='json')
    assert reponse.status_code == 200
    assert reponse.data == {'disponible': False, 'fautes': []}
    # Paused: the next checks do not wait for LanguageTool
    hote.post(VERIFIER, {'texte': 'Une autre mason'}, format='json')
    assert len(faux.requetes) == 1


def test_reponse_lente_sans_pause_pour_tous(hote, languagetool):
    faux = languagetool(erreur=requests.ReadTimeout('trop lent'))
    # A slow answer: nothing for this check, but the next ones still ask LanguageTool
    for _ in range(services.ECHECS_AVANT_PAUSE - 1):
        assert hote.post(VERIFIER, {'texte': 'Une mason'}, format='json').data['disponible'] is False
    assert len(faux.requetes) == services.ECHECS_AVANT_PAUSE - 1
    # Too slow several times in a row: paused like a breakdown
    hote.post(VERIFIER, {'texte': 'Une mason'}, format='json')
    hote.post(VERIFIER, {'texte': 'Une mason'}, format='json')
    assert len(faux.requetes) == services.ECHECS_AVANT_PAUSE


def test_une_reussite_efface_les_lenteurs(hote, languagetool):
    faux = languagetool(erreur=requests.ReadTimeout('trop lent'))
    for _ in range(services.ECHECS_AVANT_PAUSE - 1):
        hote.post(VERIFIER, {'texte': 'Une mason'}, format='json')
    faux.erreur = None
    assert hote.post(VERIFIER, {'texte': 'Une mason'}, format='json').data['disponible'] is True
    faux.erreur = requests.ReadTimeout('trop lent')
    hote.post(VERIFIER, {'texte': 'Une mason'}, format='json')
    faux.erreur = None
    # One slow answer after a success: not paused
    assert hote.post(VERIFIER, {'texte': 'Une mason'}, format='json').data['disponible'] is True


def test_reponse_illisible(hote, languagetool, monkeypatch):
    languagetool()

    class Illisible:
        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError('pas du JSON')

    monkeypatch.setattr(services.requests, 'post', lambda *a, **k: Illisible())
    assert hote.post(VERIFIER, {'texte': 'Une mason'}, format='json').data['disponible'] is False


def test_correcteur_desactive(hote, languagetool, settings):
    faux = languagetool()
    settings.CORRECTEUR = {'URL': '', 'DELAI': 5}
    assert hote.post(VERIFIER, {'texte': 'Une mason'}, format='json').data == {'disponible': False, 'fautes': []}
    assert faux.requetes == []


def test_texte_vide_sans_appel(hote, languagetool):
    faux = languagetool()
    assert hote.post(VERIFIER, {'texte': '  \n '}, format='json').data == {'disponible': True, 'fautes': []}
    assert faux.requetes == []
