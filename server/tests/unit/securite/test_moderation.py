import json

import pytest

from apps.securite import moderation
from apps.securite.moderation import ALLOW, BLOCK, WARN, analyze, normalize

NORMAL_MESSAGES = [
    "Bonjour, le logement est-il disponible du 12/10/2026 au 15/10/2026 ?",
    "Nous serons 2 adultes et 3 enfants, arrivée vers 14h30.",
    "Le prix est de 150 000 FCFA la nuit, petit-déjeuner compris.",
    "Je vais vous retrouver à l'aéroport à 18h.",
    "Je vais vous prendre à la gare routière.",
    "Je vais vous descendre les valises à votre arrivée.",
    "Vous allez le payer à l'arrivée ou en ligne ?",
    "Vous allez me payer par le site, c'est plus sûr.",
    "Ferme la porte en partant s'il te plaît.",
    "Avez-vous un chien ? Les animaux sont acceptés.",
    "Votre chien est le bienvenu.",
    "La chambre est minable, la photo ne correspond pas.",
    "Le wifi est nul depuis ce matin.",
    "La salle de bain est sale, pouvez-vous envoyer quelqu'un ?",
    "Une salle nulle pour ce prix.",
    "C'est de la merde, ce quartier la nuit.",
    "Mort de rire, la photo du chat !",
    "Ce film va te tuer de rire.",
    "Je suis mort de fatigue après le vol.",
    "Êtes-vous malade ? Je peux décaler.",
    "Tu es où ? Je suis devant le portail.",
    "Est-ce que tu es arrivé ?",
    "Vous êtes confirmé pour le 12.",
    "La clé est sous le pot de fleurs.",
    "Je vais frapper à la porte vers 20h.",
    "Il fait très chaud, on va mourir de chaud sans climatisation.",
    "Je vais porter plainte si la caution n'est pas rendue.",
    "Vous êtes un hôte formidable, merci pour tout !",
    "Tu es génial, merci pour l'accueil.",
    "Le quartier est calme, les voisins sont gentils.",
    "Pouvez-vous me rappeler les horaires du check-out ?",
    "Le gardien s'appelle Kofi, il vous ouvrira.",
    "Le code du portail est 1234.",
    "Il y a un concert ce soir sur la plage.",
    "La maison fait 120 m2 avec un jardin.",
    "Le taxi coûte environ 3 000 F depuis l'aéroport.",
    "Je suis désolé pour le retard, l'avion a été décalé.",
    "La piscine est-elle chauffée ?",
    "Est-ce qu'il y a des moustiquaires dans les chambres ?",
    "Mon mari et moi arrivons demain.",
    "Vous êtes très réactif, merci.",
    "Le ménage n'a pas été fait, c'est inadmissible.",
    "Je suis très déçu, ce n'est pas du tout comme sur les photos.",
    "Je vais laisser un avis honnête.",
    "Pouvez-vous me faire un geste sur le prix ?",
    "Le groupe électrogène fait trop de bruit.",
    "Est-ce que je peux arriver plus tôt ?",
    "Bonne nuit et à demain !",
    "Hello, is the apartment available next week?",
    "Do you have a dog? I am allergic.",
    "Are you a dog person? We travel with ours.",
    "Can you take the trash out before we arrive?",
    "Thank you, you are a star!",
    "You're right, the price includes breakfast.",
    "I'll knock on the door when I arrive.",
    "We are dying to see the beach.",
    "The room was hot, the AC is broken.",
    "Please send me a photo of the bathroom.",
    "You will love the view from the terrace.",
]

ABUSIVE_MESSAGES = [
    ("Tu es un imbécile", BLOCK, 'insult'),
    ("T'es qu'un c0nnard", BLOCK, 'insult'),
    ("Espèce de c o n", BLOCK, 'insult'),
    ("Vous êtes vraiment nul", BLOCK, 'insult'),
    ("connnnnnard", BLOCK, 'insult'),
    ("tu es une s​alope", BLOCK, 'insult'),
    ("idiot que tu es", BLOCK, 'insult'),
    ("tu es un 1d10t", BLOCK, 'insult'),
    ("fils de pute", BLOCK, 'insult'),
    ("ta gueule", BLOCK, 'insult'),
    ("Vous êtes un escroc", WARN, 'insult'),
    ("sale noir", BLOCK, 'hate'),
    ("mort aux juifs", BLOCK, 'hate'),
    ("retourne dans ton pays", BLOCK, 'hate'),
    ("je vais te tuer", BLOCK, 'threat'),
    ("Je vous tue", BLOCK, 'threat'),
    ("Je vais brûler ta maison", BLOCK, 'threat'),
    ("je sais où vous habitez", WARN, 'threat'),
    ("tu vas le regretter", WARN, 'threat'),
    ("envoie moi des nudes", BLOCK, 'harassment'),
    ("t'es bonne", WARN, 'harassment'),
    ("fuck you", BLOCK, 'insult'),
    ("you are an idiot", BLOCK, 'insult'),
    ("you fucking moron", BLOCK, 'insult'),
    ("i'm gonna kill you", BLOCK, 'threat'),
    ("go back to your country", BLOCK, 'hate'),
    ("you're so hot", WARN, 'harassment'),
]


@pytest.mark.parametrize('text', NORMAL_MESSAGES)
def test_normal_messages_are_allowed(text):
    assert analyze(text).level == ALLOW


@pytest.mark.parametrize('text,level,category', ABUSIVE_MESSAGES)
def test_abusive_messages_are_detected(text, level, category):
    result = analyze(text)
    assert result.level == level
    assert category in result.categories


def test_normalization_undoes_disguises():
    assert normalize("C0NNARD") == "conard"
    assert normalize("c.o.n.n.a.r.d") == "conard"
    assert normalize("co​nnard") == "conard"
    assert normalize("Imbécile !!!") == "imbecile"
    assert normalize("idioooot") == "idiot"
    assert normalize("150 000 FCFA") == "150 0 fcfa"


def test_most_severe_level_wins_and_categories_are_merged():
    result = analyze("Tu es un idiot, tu vas le regretter")
    assert result.level == BLOCK
    assert result.categories == ('insult', 'threat')


def test_lexicon_is_extensible_with_data(tmp_path):
    (tmp_path / 'custom.json').write_text(json.dumps({
        'targets': ['tu es'], 'fillers': ['un'],
        'entries': [{'category': 'insult', 'level': 'block', 'targeted': True, 'terms': ['zozo']}],
    }), encoding='utf-8')
    assert analyze("tu es un zozo", tmp_path).level == BLOCK
    assert analyze("le zozo du quartier", tmp_path).level == ALLOW


def test_invalid_lexicon_entry_is_rejected(tmp_path):
    (tmp_path / 'broken.json').write_text(json.dumps({
        'entries': [{'category': 'spam', 'level': 'block', 'terms': ['x']}],
    }), encoding='utf-8')
    with pytest.raises(ValueError):
        analyze("x", tmp_path)


@pytest.mark.parametrize('value,expected', [
    ('enforce', 'enforce'), ('OFF', 'off'), ('observe', 'observe'), ('', 'observe'), ('strict', 'observe'),
])
def test_mode_defaults_to_observe(settings, value, expected):
    settings.MODERATION = {**settings.MODERATION, 'MODE': value}
    assert moderation.mode() == expected


def test_excerpt_is_short():
    assert len(moderation.excerpt("a" * 500)) == moderation.EXCERPT_LENGTH
    assert moderation.excerpt("  court   texte ") == "court texte"
