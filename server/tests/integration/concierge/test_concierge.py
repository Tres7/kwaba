"""AI Concierge: Kwa-Ba tools and conversation loop. The Gemini API is simulated (no network call)."""
import json
from datetime import timedelta
from types import SimpleNamespace as NS
from unittest import mock

import pytest
from django.utils import timezone
from google.genai._gaos.lib import compat_errors
from rest_framework.test import APIClient

from apps.concierge import outils, services
from apps.concierge.models import ConversationModel, MessageModel

CONVERSATIONS = '/api/v1/concierge/conversations/'


@pytest.fixture
def concierge(settings):
    settings.CONCIERGE = {**settings.CONCIERGE, 'API_KEY': 'cle-test', 'MAX_PAR_HEURE': 20, 'MAX_PAR_JOUR': 60,
                          'RECHERCHE_WEB': True, 'MODELE': 'gemini-3.8-flash', 'REFLEXION': 'low'}
    return settings


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# --- Faux client Gemini (API Interactions en streaming) --------------------------------------

def tour(interaction_id, texte='', appels=(), statut=None):
    """SSE events of a turn: text in two chunks, function calls, end."""
    evts = [NS(event_type='interaction.created', interaction=NS(id=interaction_id))]
    index = 0
    if texte:
        evts.append(NS(event_type='step.start', index=index, step=NS(type='model_output')))
        moitie = len(texte) // 2
        for morceau in (texte[:moitie], texte[moitie:]):
            evts.append(NS(event_type='step.delta', index=index, delta=NS(type='text', text=morceau)))
        index += 1
    for nom, args in appels:
        evts.append(NS(event_type='step.start', index=index, step=NS(type='function_call', id=f'call_{index}', name=nom, arguments={})))
        evts.append(NS(event_type='step.delta', index=index, delta=NS(type='arguments_delta', arguments=json.dumps(args))))
        index += 1
    etapes = [NS(type='function_call', id=f'call_{i + (1 if texte else 0)}', name=n, arguments=a) for i, (n, a) in enumerate(appels)]
    evts.append(NS(event_type='interaction.completed', interaction=NS(
        id=interaction_id, status=statut or ('requires_action' if appels else 'completed'), steps=etapes,
        usage=NS(total_input_tokens=1000, total_output_tokens=200, total_thought_tokens=50))))
    return evts


class FauxGemini:
    def __init__(self, *tours):
        self.tours = list(tours)
        self.requetes = []
        self.interactions = NS(create=self._create)

    def _create(self, **kwargs):
        self.requetes.append(json.loads(json.dumps(kwargs, default=str)))
        suivant = self.tours.pop(0)
        if isinstance(suivant, Exception):
            raise suivant
        return iter(suivant)


def _evenements(response):
    brut = b''.join(response.streaming_content).decode()
    return [(bloc.split('\n')[0][7:], json.loads(bloc.split('\n')[1][6:])) for bloc in brut.strip().split('\n\n')]


# --- Outils ------------------------------------------------------------------------------

def test_recherche_de_logements_reels_avec_cout_du_sejour(make_hebergement):
    make_hebergement(name='Appart Bè', city='Lomé', price_per_night=30000, max_guests=2, rating=4.8)
    make_hebergement(name='Villa Baguida', city='Lomé', price_per_night=80000, max_guests=6)
    make_hebergement(name='Hôtel Cotonou', city='Cotonou', price_per_night=20000)
    arrivee = timezone.localdate() + timedelta(days=20)

    resultat, cartes = outils.rechercher_logements({
        'ville': 'lomé', 'arrivee': arrivee.isoformat(), 'depart': (arrivee + timedelta(days=5)).isoformat(),
        'voyageurs': 2, 'budget_max_nuit': 50000,
    })
    assert [r['nom'] for r in resultat['resultats']] == ['Appart Bè']
    assert resultat['resultats'][0]['cout_total_sejour_fcfa'] == 159000  # 5 x 30 000 + 6 %
    assert cartes[0]['type'] == 'logement' and cartes[0]['total'] == 159000

    vide, _ = outils.rechercher_logements({'ville': 'Kigali'})
    assert vide['resultats'] == [] and 'ne recommande pas' in vide['message']


def test_entrees_invalides_renvoyees_en_erreur_au_modele():
    contenu, cartes, erreur = outils.executer('rechercher_logements', {'ville': 'Lomé', 'arrivee': '12/11/2026'})
    assert erreur and 'date invalide' in contenu and cartes == []
    assert outils.executer('rechercher_logements', None)[2] is True
    assert outils.executer('outil_inconnu', {})[2] is True


def test_devis_transfert_et_aeroport_non_desservi():
    jour = (timezone.localdate() + timedelta(days=10)).isoformat()
    resultat, cartes = outils.devis_transfert({'aeroport': 'lfw', 'arrivee': f'{jour}T23:30', 'passagers': 2, 'bagages': 2})
    # Arrival at 11:30 pm: same price as by day (night surcharge removed)
    assert resultat['options'][0]['prix'] == 10000 and 'nuit' not in resultat['options'][0]
    assert 'nuit' in resultat['regles'] and '25' not in resultat['regles']
    assert cartes[0]['type'] == 'transfert' and cartes[0]['arrivee'] == f'{jour}T23:30'
    inconnu, _ = outils.devis_transfert({'aeroport': 'CDG', 'arrivee': f'{jour}T10:00', 'passagers': 1, 'bagages': 1})
    assert 'non desservi' in inconnu['erreur'] and 'Lomé (LFW)' in inconnu['erreur']


def test_declarations_de_fonctions_au_format_gemini():
    for d in outils.DEFINITIONS:
        assert d['type'] == 'function' and d['parameters']['type'] == 'object'
        # No "string or null" types: not supported by Gemini's schema
        assert all(isinstance(p['type'], str) for p in d['parameters']['properties'].values())


# --- Boucle de conversation ------------------------------------------------------------------

def test_conversation_avec_fonction_puis_reponse(concierge, make_user, make_hebergement):
    h = make_hebergement(name='Appart Bè', city='Lomé', price_per_night=30000)
    faux = FauxGemini(
        tour('int_1', 'Je regarde les logements à Lomé.', [('rechercher_logements', {'ville': 'Lomé', 'voyageurs': 2})]),
        tour('int_2', "L'**Appart Bè** est idéal pour vous deux."),
        tour('int_3', 'Avec plaisir !'),
    )
    client = _client(make_user())
    cid = client.post(CONVERSATIONS).data['id']
    with mock.patch.object(services, '_client', return_value=faux):
        evts = _evenements(client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': 'Un appart à Lomé pour 2'}, format='json'))

    types = [e for e, _ in evts]
    assert types[0] == 'texte' and 'outil' in types and 'cartes' in types and types[-1] == 'fin'
    assert next(d for e, d in evts if e == 'cartes')['cartes'][0]['id'] == str(h.id)

    # First call: model, thinking, system instruction, functions + Google search, without a previous interaction
    req = faux.requetes[0]
    assert (req['model'], req['generation_config'], req['stream']) == ('gemini-3.8-flash', {'thinking_level': 'low'}, True)
    assert 'Concierge Kwa-Ba' in req['system_instruction'] and 'Date du jour' in req['system_instruction']
    assert [t.get('name', t['type']) for t in req['tools']] == [
        'rechercher_logements', 'devis_transfert', 'proposer_voyage_de_groupe', 'google_search']
    assert 'previous_interaction_id' not in req and req['input'] == 'Un appart à Lomé pour 2'
    # Second call: function result attached to the previous interaction
    req2 = faux.requetes[1]
    assert req2['previous_interaction_id'] == 'int_1'
    resultat = req2['input'][0]
    assert (resultat['type'], resultat['call_id'], resultat['name']) == ('function_result', 'call_1', 'rechercher_logements')
    assert 'Appart Bè' in resultat['result'][0]['text']

    affichage = client.get(f'{CONVERSATIONS}{cid}/').data
    assert affichage['titre'] == 'Un appart à Lomé pour 2'
    assert [(m['role'], bool(m['cartes'])) for m in affichage['messages']] == [('user', False), ('assistant', False), ('assistant', True)]
    assert ConversationModel.objects.get(pk=cid).interaction_id == 'int_2'

    # Next message: the conversation goes on from the last interaction
    with mock.patch.object(services, '_client', return_value=faux):
        _evenements(client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': 'Merci'}, format='json'))
    assert faux.requetes[2]['previous_interaction_id'] == 'int_2'


def test_interaction_expiree_reprise_avec_resume(concierge, make_user):
    user = make_user()
    conv = ConversationModel.objects.create(utilisateur=user, titre='Lomé', interaction_id='int_ancienne')
    MessageModel.objects.create(conversation=conv, role='user', texte='Je pars à Lomé en mai')
    MessageModel.objects.create(conversation=conv, role='assistant', texte='Belle idée, mai est chaud.')
    expiree = compat_errors.NotFoundError('interaction introuvable', response=mock.Mock(status_code=404), body=None)
    faux = FauxGemini(expiree, tour('int_neuve', 'Bien sûr.'))
    with mock.patch.object(services, '_client', return_value=faux):
        evts = _evenements(_client(user).post(f'{CONVERSATIONS}{conv.id}/messages/', {'texte': 'Et le budget ?'}, format='json'))
    assert evts[-1][0] == 'fin'
    reprise = faux.requetes[1]
    assert 'previous_interaction_id' not in reprise
    assert 'Je pars à Lomé en mai' in reprise['input'] and 'Et le budget ?' in reprise['input']
    conv.refresh_from_db()
    assert conv.interaction_id == 'int_neuve'


def test_quota_recherche_google_continue_sans_elle(concierge, make_user):
    quota = compat_errors.RateLimitError('quota', response=mock.Mock(status_code=429), body=None)
    faux = FauxGemini(quota, tour('int_b', 'Voici mes idées.'), tour('int_c', 'Encore une idée.'))
    client = _client(make_user())
    cid = client.post(CONVERSATIONS).data['id']
    with mock.patch.object(services, '_client', return_value=faux):
        evts = _evenements(client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': 'Restaurants à Lomé ?'}, format='json'))
        assert evts[-1][0] == 'fin'
        _evenements(client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': 'Et à Cotonou ?'}, format='json'))
    noms = [[t.get('name', t['type']) for t in r['tools']] for r in faux.requetes]
    assert 'google_search' in noms[0] and 'google_search' not in noms[1]
    assert 'google_search' not in noms[2]  # disabled for a few minutes, no useless wait


def test_reponse_bloquee_ecartee(concierge, make_user):
    faux = FauxGemini(tour('int_x', 'partiel', statut='failed'))
    client = _client(make_user())
    cid = client.post(CONVERSATIONS).data['id']
    with mock.patch.object(services, '_client', return_value=faux):
        evts = _evenements(client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': 'Question hors sujet'}, format='json'))
    assert evts[-1][0] == 'refus'
    assert not MessageModel.objects.filter(conversation_id=cid, role='assistant').exists()


def test_quota_inactif_et_confidentialite(concierge, make_user, settings):
    user = make_user()
    client = _client(user)
    cid = client.post(CONVERSATIONS).data['id']
    assert _client(make_user()).get(f'{CONVERSATIONS}{cid}/').status_code == 404
    assert client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': ''}, format='json').status_code == 400

    settings.CONCIERGE = {**settings.CONCIERGE, 'MAX_PAR_HEURE': 1}
    faux = FauxGemini(tour('int_a', 'Bonjour !'))
    with mock.patch.object(services, '_client', return_value=faux):
        assert client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': 'Salut'}, format='json').status_code == 200
        trop = client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': 'Encore'}, format='json')
    assert trop.status_code == 429 and 'limite' in trop.data['detail']

    settings.CONCIERGE = {**settings.CONCIERGE, 'API_KEY': ''}
    assert client.get('/api/v1/concierge/statut/').data == {'actif': False}
    assert client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': 'x'}, format='json').status_code == 503


def test_version_anglaise_du_site(concierge, make_user, make_hebergement):
    """From kwa-ba.com/en, the Concierge is told to answer in English and its step messages are translated."""
    make_hebergement(name='Appart Bè', city='Lomé', price_per_night=30000)
    faux = FauxGemini(
        tour('int_1', 'Looking at places in Lomé.', [('rechercher_logements', {'ville': 'Lomé', 'voyageurs': 2})]),
        tour('int_2', 'Appart Bè is ideal for you both.'),
    )
    client = _client(make_user())
    cid = client.post(CONVERSATIONS).data['id']
    with mock.patch.object(services, '_client', return_value=faux):
        evts = _evenements(client.post(f'{CONVERSATIONS}{cid}/messages/', {'texte': 'A flat in Lomé for 2'}, format='json',
                                       HTTP_ACCEPT_LANGUAGE='en'))
    assert 'Réponds en anglais' in faux.requetes[0]['system_instruction']
    assert next(d for e, d in evts if e == 'outil')['libelle'] == 'Looking for places to stay'

    # Without a header (or in French): usual instruction, messages in French
    assert services.langue_de('') == 'fr' and services.langue_de('fr-FR,fr;q=0.9') == 'fr' and services.langue_de('en-GB') == 'en'
    assert 'Réponds en anglais' not in services._systeme('fr')
    assert services._m('sollicite', 'en').startswith('The Concierge is very busy')


def test_erreurs_en_anglais(concierge, make_user):
    """English version: step and error messages translated (web search, Gemini unreachable, conversation too long)."""
    recherche = [NS(event_type='step.start', index=0, step=NS(type='google_search_call'))]
    coupure = compat_errors.APIConnectionError(request=mock.Mock())
    faux = FauxGemini(recherche + tour('int_w', 'Here are some ideas.'), coupure)
    client = _client(make_user())
    cid = client.post(CONVERSATIONS).data['id']
    url = f'{CONVERSATIONS}{cid}/messages/'
    with mock.patch.object(services, '_client', return_value=faux):
        evts = _evenements(client.post(url, {'texte': 'Restaurants in Lomé?'}, format='json', HTTP_ACCEPT_LANGUAGE='en'))
        assert ('outil', {'nom': 'google_search', 'libelle': services._m('web', 'en')}) in evts
        evts = _evenements(client.post(url, {'texte': 'And in Cotonou?'}, format='json', HTTP_ACCEPT_LANGUAGE='en'))
        assert evts[-1] == ('erreur', {'message': 'The Concierge is temporarily unavailable. Please try again.'})
        with mock.patch.object(services, 'MAX_MESSAGES_PAR_CONVERSATION', 0):
            evts = _evenements(client.post(url, {'texte': 'Hello'}, format='json', HTTP_ACCEPT_LANGUAGE='en'))
    assert evts == [('erreur', {'message': 'This conversation is long: start a new one to continue.'})]
