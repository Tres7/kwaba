"""Anti-bypass: contact details hidden in messages and listings, anonymous traveller before payment,
alerts for the back-office."""
import pytest
from django.core import mail

from apps.messaging.infrastructure.persistence.models import MessageModel, NotificationOutboxModel
from apps.securite.coordonnees import MASQUE, analyser
from apps.securite.models import AlerteFraudeModel

CONVERSATIONS = '/api/v1/messaging/conversations/'


@pytest.fixture
def listing(make_hebergement):
    return make_hebergement(name='Villa Océane')


@pytest.fixture
def guest(make_user):
    return make_user(first_name='Ama', last_name='Mensah')


@pytest.fixture
def thread(client_for, guest, listing):
    return client_for(guest).post(CONVERSATIONS, {'hebergement_id': str(listing.id)}, format='json').data['id']


def _envoyer(client, thread, texte):
    return client.post(f'{CONVERSATIONS}{thread}/messages/', {'content': texte}, format='json')


@pytest.mark.parametrize('texte', [
    'Appelez-moi au 90 12 34 56', 'whatsapp +228-90-12-34-56', 'kofi.mensah@gmail.com', 'kofi arobase gmail point com',
    'https://wa.me/22890123456', 'mon insta @villa_lome', 'neuf zéro un deux trois quatre cinq six',
])
def test_coordonnees_detectees(texte):
    masque, trouvailles = analyser(texte)
    assert MASQUE in masque and trouvailles


@pytest.mark.parametrize('texte', [
    'Arrivée le 12/10/2026, départ le 15/10/2026', 'Le prix est de 150 000 FCFA la nuit', 'Entre 25 000 et 35 000 F',
    'Nous serons 2 adultes et 3 enfants, arrivée vers 14h30', 'La maison fait 120 m2', 'Voir kwa-ba.com',
    'Total 1 250 000 FCFA pour 10 nuits', 'ok.ne t inquiète pas', 'Le code du portail est 1234',
])
def test_textes_ordinaires_intacts(texte):
    assert analyser(texte) == (texte, [])


def test_message_masque_et_signale(client_for, guest, listing, thread):
    reponse = _envoyer(client_for(guest), thread, 'Bonjour, je préfère vous payer en espèces : 90 12 34 56 ou ama@gmail.com')
    assert reponse.status_code == 201
    assert reponse.data['masked'] is True
    assert '90 12 34 56' not in reponse.data['content'] and 'ama@gmail.com' not in reponse.data['content']
    assert MessageModel.objects.get().content.count(MASQUE) == 2  # the original text is not kept
    recu = client_for(listing.host).get(f'{CONVERSATIONS}{thread}/messages/').data['results'][0]
    assert recu['masked'] is True and MASQUE in recu['content']
    alerte = AlerteFraudeModel.objects.get()
    assert alerte.utilisateur == guest and alerte.contexte == 'message' and alerte.masquee
    assert set(alerte.types) == {'telephone', 'email', 'hors_site'} and '90 12 34 56' in alerte.extraits
    # Message ordinaire : ni masque ni alerte
    assert _envoyer(client_for(guest), thread, 'Le logement est-il libre du 12/10/2026 au 15/10/2026 ?').data['masked'] is False
    assert AlerteFraudeModel.objects.count() == 1


def test_masque_aussi_apres_paiement(client_for, guest, listing, thread, make_reservation):
    make_reservation(listing, guest=guest)
    assert _envoyer(client_for(listing.host), thread, 'Mon numéro : 90 12 34 56').data['masked'] is True


def test_voyageur_anonyme_jusqu_au_paiement(client_for, guest, listing, thread, make_reservation):
    hote = client_for(listing.host)
    _envoyer(client_for(guest), thread, 'Bonjour, la villa a-t-elle la climatisation ?')
    fil = hote.get(f'{CONVERSATIONS}{thread}/').data
    assert fil['booked'] is False
    assert fil['other_participant']['first_name'] == 'Voyageur' and fil['other_participant']['last_name'] == ''
    assert fil['other_participant']['avatar_url'] is None
    assert hote.get(CONVERSATIONS).data['results'][0]['other_participant']['first_name'] == 'Voyageur'
    # The notification email to the host does not name the traveller either
    assert NotificationOutboxModel.objects.get().payload['sender_first_name'] == 'Un voyageur'
    # The traveller sees the host normally
    assert client_for(guest).get(f'{CONVERSATIONS}{thread}/').data['other_participant']['first_name'] == listing.host.first_name

    make_reservation(listing, guest=guest, status='pending')  # booked but not paid: still anonymous
    assert hote.get(f'{CONVERSATIONS}{thread}/').data['other_participant']['first_name'] == 'Voyageur'
    make_reservation(listing, guest=guest, starts_in=40)  # paid
    fil = hote.get(f'{CONVERSATIONS}{thread}/').data
    assert fil['booked'] is True and fil['other_participant']['first_name'] == 'Ama'
    assert fil['other_participant']['last_name'] == 'Mensah'


def test_hote_ecrit_seulement_apres_paiement(client_for, guest, listing, make_reservation):
    hote = client_for(listing.host)
    en_attente = make_reservation(listing, guest=guest, status='pending')
    assert hote.post(f'{CONVERSATIONS}avec-voyageur/', {'reservation_id': str(en_attente.id)}, format='json').status_code == 404
    payee = make_reservation(listing, guest=guest, starts_in=40)
    assert hote.post(f'{CONVERSATIONS}avec-voyageur/', {'reservation_id': str(payee.id)}, format='json').status_code == 201


def test_admins_prevenus_au_troisieme_signalement(client_for, guest, thread, make_user, django_capture_on_commit_callbacks):
    make_user(role='admin', email='admin@kwa-ba.com')
    client = client_for(guest)
    with django_capture_on_commit_callbacks(execute=True):
        for i in range(4):
            _envoyer(client, thread, f'Écrivez-moi : ama{i}@gmail.com')
    alertes = [m for m in mail.outbox if 'Anti-fraude' in m.subject]
    assert len(alertes) == 1 and alertes[0].to == ['admin@kwa-ba.com']
    assert AlerteFraudeModel.objects.count() == 4


def test_annonce_sans_coordonnees(client_for, make_user, make_hebergement, listing):
    hote = make_user(role='hote')
    donnees = {'name': 'Villa Lomé', 'description': 'Belle villa. Réservez au 90 12 34 56 !', 'type': 'villa', 'city': 'Lomé',
               'location': 'Bè', 'price_per_night': 30000, 'max_guests': 4, 'amenities': [], 'surface_m2': 90, 'chambres': 2,
               'lits_doubles': 2, 'petit_dejeuner': 'non'}
    reponse = client_for(hote).post('/api/v1/hebergements/', donnees, format='json')
    assert reponse.status_code == 400 and 'messagerie Kwa-Ba' in str(reponse.data['description'])
    assert AlerteFraudeModel.objects.get(contexte='annonce').utilisateur == hote
    # Listing published before the filtering: hidden for travellers, intact for its host
    listing.description = 'Contact WhatsApp 90 12 34 56'
    listing.save()
    public = client_for(make_user()).get(f'/api/v1/hebergements/{listing.id}/').data
    assert '90 12 34 56' not in public['description'] and MASQUE in public['description']


def test_back_office_anti_fraude(client_for, make_user, guest, thread):
    _envoyer(client_for(guest), thread, 'Appelez-moi au 90 12 34 56')
    admin = client_for(make_user(role='admin'))
    assert client_for(guest).get('/api/v1/admin/anti-fraude/').status_code == 403
    page = admin.get('/api/v1/admin/anti-fraude/').data
    assert page['count'] == 1
    alerte = page['results'][0]
    assert alerte['utilisateur']['email'] == guest.email and alerte['types'] == ['Téléphone'] and alerte['utilisateur']['nb_alertes'] == 1
    traitee = admin.post(f"/api/v1/admin/anti-fraude/{alerte['id']}/traiter/", {'note': 'Averti par email'}, format='json')
    assert traitee.status_code == 200 and traitee.data['traitee'] is True
    assert admin.get('/api/v1/admin/anti-fraude/').data['count'] == 0
    assert admin.get('/api/v1/admin/anti-fraude/', {'statut': 'traitees'}).data['count'] == 1
