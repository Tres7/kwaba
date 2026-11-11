"""Spelling checker: language of each part of a text and positions in UTF-16 (no database, no LanguageTool)."""
from apps.correcteur.services import classer_suggestions, extrait_utf16, langue_de, longueur_utf16, segments


def test_langue_des_mots_courants():
    assert langue_de('Villa avec piscine près de la plage') == 'fr'
    assert langue_de('Beach house with a pool, close to the market') == 'en'
    # Nothing that tells: the caller decides
    assert langue_de('Wifi, climatisation, parking') is None


def test_description_en_francais_puis_en_anglais():
    texte = "Belle maison dans le quartier de Bè.\n- Wifi\n\nBeautiful house in the Bè district.\n- Parking"
    parties = segments(texte, 'fr')
    assert [langue for _, _, langue in parties] == ['fr', 'en']
    # The line that does not tell (« - Wifi ») stays with the French part, the parts cover the text in order
    assert texte[parties[0][0]:parties[0][1]] == "Belle maison dans le quartier de Bè.\n- Wifi"
    assert texte[parties[1][0]:parties[1][1]] == "Beautiful house in the Bè district.\n- Parking"


def test_premieres_lignes_sans_indice_et_langue_du_site():
    # The first lines take the language of the first line that tells
    assert [langue for _, _, langue in segments('Lomé\nThe house is near the beach', 'fr')] == ['en']
    # Nothing tells: language of the site
    assert segments('Wifi, parking', 'en') == [(0, 13, 'en')]
    assert segments('', 'fr') == []


def test_positions_utf16_comme_le_navigateur():
    texte = 'Super 🌴 mason'
    # The emoji counts for 2, like in JavaScript and in LanguageTool (Java)
    assert longueur_utf16('🌴') == 2
    assert extrait_utf16(texte, 9, 5) == 'mason'


def test_suggestions_les_plus_proches_d_abord():
    # Order given by LanguageTool for « Deriere » (seen on 2026-11-11)
    assert classer_suggestions('Deriere', ["D'arrière", "D'arriéré", "D'Épierre", 'Derrière'])[0] == 'Derrière'
    # A split word comes after the real words; equal ones keep the order of LanguageTool
    assert classer_suggestions('pisine', ['piscine', 'Pikine', 'pi sine']) == ['piscine', 'Pikine', 'pi sine']
    assert classer_suggestions('Beautifull', ['Beautiful', 'Beautifully']) == ['Beautiful', 'Beautifully']
    # The apostrophe is kept when the host typed one
    assert classer_suggestions("lappartement", ["l'appartement", 'appartement']) == ['appartement', "l'appartement"]
    assert classer_suggestions("d'apartement", ["d'appartement", 'dappartement']) == ["d'appartement", 'dappartement']
    # Capitals count: the name « Mason » does not jump before « maison » (it would without its capital)
    assert classer_suggestions('mason', ['maison', 'Mason']) == ['maison', 'Mason']
    assert classer_suggestions('Kpalime', ['Palme', 'Kpalimé']) == ['Kpalimé', 'Palme']
