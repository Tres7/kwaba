"""Listing details: area, bedrooms, beds, breakfast, times."""
HEBERGEMENTS = '/api/v1/hebergements/'


def _annonce(**extra):
    return {
        'latitude': 6.13, 'longitude': 1.22,
        'name': 'Villa Océane', 'type': 'villa', 'city': 'Lomé', 'location': 'Baguida', 'price_per_night': 85000,
        'max_guests': 6, 'amenities': ['wifi'], 'image_url': 'https://images.unsplash.com/photo-1.jpg',
        'surface_m2': 140, 'chambres': 3, 'salles_de_bain': 2, 'lits_doubles': 2, 'lits_simples': 2, 'canapes_lits': 0,
        'petit_dejeuner': 'inclus', 'arrivee_a_partir': '14:00', 'depart_avant': '11:00', **extra,
    }


def test_details_enregistres_et_publics(client_for, make_user, api_client, make_hebergement):
    reponse = client_for(make_user(role='hote')).post(HEBERGEMENTS, _annonce(), format='json')
    assert reponse.status_code == 201, reponse.data
    d = reponse.data
    assert (d['surface_m2'], d['chambres'], d['salles_de_bain'], d['lits_doubles'], d['lits_simples']) == (140, 3, 2, 2, 2)
    assert d['petit_dejeuner'] == 'inclus' and d['arrivee_a_partir'] == '14:00:00' and d['depart_avant'] == '11:00:00'


def test_details_obligatoires_a_la_creation(client_for, make_user):
    corps = _annonce()
    for champ in ('surface_m2', 'chambres', 'petit_dejeuner'):
        corps.pop(champ)
    corps.update(lits_doubles=0, lits_simples=0)
    reponse = client_for(make_user(role='hote')).post(HEBERGEMENTS, corps, format='json')
    assert reponse.status_code == 400
    assert {'surface_m2', 'chambres', 'petit_dejeuner', 'lits'} <= set(reponse.data)


def test_petit_dejeuner_en_option_exige_un_prix(client_for, make_user):
    client = client_for(make_user(role='hote'))
    assert client.post(HEBERGEMENTS, _annonce(petit_dejeuner='option'), format='json').status_code == 400
    reponse = client.post(HEBERGEMENTS, _annonce(petit_dejeuner='option', petit_dejeuner_prix=3000), format='json')
    assert reponse.status_code == 201 and reponse.data['petit_dejeuner_prix'] == 3000


def test_une_ancienne_annonce_se_modifie_sans_les_details(client_for, make_hebergement, make_user):
    hote = make_user(role='hote')
    ancienne = make_hebergement(host=hote)
    reponse = client_for(hote).patch(f'{HEBERGEMENTS}{ancienne.id}/', {'price_per_night': 40000}, format='json')
    assert reponse.status_code == 200 and reponse.data['surface_m2'] is None


def test_filtre_petit_dejeuner_inclus(api_client, make_hebergement):
    make_hebergement(name='Avec', petit_dejeuner='inclus')
    make_hebergement(name='Sans', petit_dejeuner='non')
    noms = [h['name'] for h in api_client.get(HEBERGEMENTS, {'petit_dejeuner': 'inclus'}).data['results']]
    assert noms == ['Avec']
