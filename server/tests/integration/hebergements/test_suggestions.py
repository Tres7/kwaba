URL = '/api/v1/hebergements/suggestions/'


def test_ville_trouvee_sans_accent_ni_majuscule(api_client, make_hebergement):
    make_hebergement(city='Lomé')
    make_hebergement(city='Lomé')
    make_hebergement(city='Kpalimé')

    reponse = api_client.get(URL, {'q': 'LOME'})

    assert reponse.status_code == 200
    assert reponse.data['villes'] == [{'city': 'Lomé', 'count': 2}]


def test_villes_commencant_par_la_saisie_en_premier(api_client, make_hebergement):
    make_hebergement(city='Atakpamé')
    make_hebergement(city='Atakpamé')
    make_hebergement(city='Aného')

    reponse = api_client.get(URL, {'q': 'a'})

    # Both start with "a": the one with the most listings first
    assert [v['city'] for v in reponse.data['villes']] == ['Atakpamé', 'Aného']

    reponse = api_client.get(URL, {'q': 'pam'})
    assert [v['city'] for v in reponse.data['villes']] == ['Atakpamé']


def test_logements_par_nom(api_client, make_hebergement):
    villa = make_hebergement(name='Villa Océane', city='Lomé')
    make_hebergement(name='Studio centre', city='Lomé')

    reponse = api_client.get(URL, {'q': 'océane'})

    assert [str(logement['id']) for logement in reponse.data['logements']] == [str(villa.id)]
    assert reponse.data['logements'][0]['city'] == 'Lomé'


def test_annonces_non_publiees_jamais_proposees(api_client, make_hebergement):
    make_hebergement(name='Villa cachée', city='Sokodé', statut_verification='en_attente')

    reponse = api_client.get(URL, {'q': 'soko'})
    assert reponse.data == {'villes': [], 'logements': []}

    reponse = api_client.get(URL, {'q': 'cachée'})
    assert reponse.data['logements'] == []


def test_saisie_vide(api_client, make_hebergement):
    make_hebergement(city='Lomé')

    assert api_client.get(URL, {'q': '  '}).data == {'villes': [], 'logements': []}
    assert api_client.get(URL).data == {'villes': [], 'logements': []}
