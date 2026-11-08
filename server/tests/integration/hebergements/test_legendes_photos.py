"""Room of each photo (Chambre 1, Salon…): required for a new listing, shown to travellers."""
HEBERGEMENTS = '/api/v1/hebergements/'
A, B = 'https://images.unsplash.com/photo-a.jpg', 'https://images.unsplash.com/photo-b.jpg'


def _annonce(**extra):
    return {
        'name': 'Villa Océane', 'type': 'villa', 'city': 'Lomé', 'location': 'Baguida', 'latitude': 6.13, 'longitude': 1.22,
        'point_repere': 'Derrière la pharmacie', 'price_per_night': 85000, 'max_guests': 6, 'amenities': [],
        'chambres': 3, 'salles_de_bain': 2, 'lits_doubles': 2, 'petit_dejeuner': 'non',
        'image_url': A, 'images': [A, B], 'legendes_photos': {A: 'exterieur', B: 'chambre_2'}, **extra,
    }


def test_saved_and_public(client_for, make_user, api_client):
    reponse = client_for(make_user(role='hote')).post(HEBERGEMENTS, _annonce(), format='json')
    assert reponse.status_code == 201, reponse.data
    assert reponse.data['legendes_photos'] == {A: 'exterieur', B: 'chambre_2'}


def test_every_photo_needs_its_room(client_for, make_user):
    reponse = client_for(make_user(role='hote')).post(HEBERGEMENTS, _annonce(legendes_photos={A: 'salon'}), format='json')
    assert reponse.status_code == 400 and 'legendes_photos' in reponse.data


def test_unknown_rooms_refused(client_for, make_user):
    client = client_for(make_user(role='hote'))
    for piece in ('garage', 'chambre_0', 'chambre_51', 'chambre_un'):
        reponse = client.post(HEBERGEMENTS, _annonce(legendes_photos={A: 'salon', B: piece}), format='json')
        assert reponse.status_code == 400, piece


def test_rooms_of_removed_photos_dropped(client_for, make_user):
    client = client_for(make_user(role='hote'))
    annonce = client.post(HEBERGEMENTS, _annonce(), format='json').data
    reponse = client.patch(f"{HEBERGEMENTS}{annonce['id']}/", {'images': [A]}, format='json')
    assert reponse.status_code == 200 and reponse.data['legendes_photos'] == {A: 'exterieur'}


def test_older_listing_changed_without_rooms(client_for, make_hebergement):
    ancienne = make_hebergement(image_url=A, images=[A, B])
    reponse = client_for(ancienne.host).patch(f'{HEBERGEMENTS}{ancienne.id}/', {'price_per_night': 30000}, format='json')
    assert reponse.status_code == 200 and reponse.data['legendes_photos'] == {}
