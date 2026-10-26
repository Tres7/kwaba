"""Contracts: prefilled issuing, electronic signature (personal link or host space), proofs and PDF."""
import base64
import json
import re
from datetime import timedelta
from io import BytesIO

import pytest
from django.core import mail
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.contrats.models import ContratModel, ModeleContratModel
from apps.documents.models import ParametresSocieteModel
from apps.securite.models import JournalAuditModel
from apps.transferts.models import ChauffeurModel
from apps.verifications.models import PieceIdentiteModel

C, A = '/api/v1/contrats/', '/api/v1/admin/contrats/'
TOUT_CONFORME = {'identite': True, 'adresse': True, 'photos': True, 'equipements': True}


@pytest.fixture(autouse=True)
def stockage(tmp_path, monkeypatch):
    for champ in ('signature', 'pdf'):
        monkeypatch.setattr(ContratModel._meta.get_field(champ), 'storage', FileSystemStorage(location=tmp_path))
    monkeypatch.setattr(ParametresSocieteModel._meta.get_field('signature_representant'), 'storage', FileSystemStorage(location=tmp_path))


@pytest.fixture
def societe():
    return ParametresSocieteModel.objects.update_or_create(pk=1, defaults={
        'raison_sociale': 'Kwa-Ba SARL', 'forme_juridique': 'SARL', 'adresse': 'Boulevard du 13 Janvier, Lomé',
        'rccm': 'TG-LOM-2026-B-1', 'nif': '1000123456', 'email': 'contact@kwa-ba.com',
        'representant_nom': 'Mendé Fadel', 'representant_qualite': 'Gérant'})[0]


@pytest.fixture
def admin(client_for, make_user):
    return client_for(make_user(role='admin'))


def _signature(vide=False) -> str:
    image = Image.new('RGBA', (600, 200), (0, 0, 0, 0))
    if not vide:
        ImageDraw.Draw(image).line([(40, 150), (200, 40), (380, 160), (560, 60)], fill=(20, 20, 60, 255), width=6)
    tampon = BytesIO()
    image.save(tampon, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(tampon.getvalue()).decode()


def _chauffeur(**extra):
    return ChauffeurModel.objects.create(prenom='Komi', nom='Adjo', telephone='+22890000001', categorie='berline',
                                         email='komi@exemple.tg', vehicule='Corolla grise', immatriculation='TG 1234 AB',
                                         pays_versement='TG', operateur_versement='togocel', numero_versement='90000001', **extra)


def _jeton(message) -> str:
    return re.search(r'/contrat/([\w-]+)', message.body).group(1)


def _pdf(reponse) -> bytes:
    assert reponse.status_code == 200, getattr(reponse, 'data', reponse)
    assert reponse['Content-Type'] == 'application/pdf'
    assert reponse.content.startswith(b'%PDF')
    return reponse.content


def test_hote_signe_son_contrat_depuis_son_espace(client_for, make_user, societe, django_capture_on_commit_callbacks):
    hote = make_user(role='hote', first_name='Ama', last_name='Mensah')
    client = client_for(hote)
    apercu = client.get(f'{C}hote/').data
    texte = ' '.join(b['texte'] for b in apercu['blocs'])
    assert apercu['statut'] == 'a_signer' and apercu['reference'] is None
    assert 'Ama Mensah' in texte and 'Kwa-Ba SARL' in texte and 'Mendé Fadel, Gérant' in texte
    assert f"joignable au {hote.phone} et à l'adresse {hote.email}, ci-après « l'Hôte »" in texte
    assert '5 %' in texte and '8 %' in texte and '{{' not in texte and '[à compléter]' not in texte
    assert not ContratModel.objects.exists()  # nothing is issued before the signature

    corps = {'nom': 'Ama Mensah', 'signature': _signature(), 'accepte': True, 'version': apercu['version']}
    assert client.post(f'{C}hote/signer/', {**corps, 'version': 99}, format='json').status_code == 409
    assert client.post(f'{C}hote/signer/', {**corps, 'accepte': False}, format='json').status_code == 400
    assert client.post(f'{C}hote/signer/', {**corps, 'signature': _signature(vide=True)}, format='json').status_code == 400
    assert client.post(f'{C}hote/signer/', {**corps, 'signature': 'data:text/html;base64,PHNjcmlwdD4='}, format='json').status_code == 400

    with django_capture_on_commit_callbacks(execute=True):
        reponse = client.post(f'{C}hote/signer/', corps, format='json', HTTP_USER_AGENT='Mozilla/5.0 Test')
    assert reponse.status_code == 200, reponse.data
    assert reponse.data['statut'] == 'signe'
    contrat = ContratModel.objects.get(hote=hote)
    assert contrat.signataire_nom == 'Ama Mensah' and contrat.methode == 'compte Kwa-Ba'
    assert contrat.ip == '127.0.0.1' and contrat.user_agent == 'Mozilla/5.0 Test'
    assert len(contrat.empreinte_texte) == 64 and len(contrat.empreinte_pdf) == 64 and contrat.pdf
    destinataires = {d for m in mail.outbox for d in m.to}
    assert {hote.email, 'contact@kwa-ba.com'} <= destinataires
    assert all(m.attachments and m.attachments[-1][0] == f'contrat-{contrat.reference}.pdf' for m in mail.outbox if 'signé' in m.subject)
    assert JournalAuditModel.objects.filter(action='contrat_signe').exists()

    _pdf(client.get(f'{C}hote/pdf/'))
    assert client.post(f'{C}hote/signer/', corps, format='json').status_code == 400  # already signed


def test_pas_de_contrat_sans_informations_legales(client_for, make_user):
    assert client_for(make_user(role='hote')).get(f'{C}hote/').status_code == 404


def test_contrat_hote_reserve_aux_hotes_avec_telephone(client_for, make_user, societe):
    assert client_for(make_user()).get(f'{C}hote/').status_code == 403  # voyageur
    sans_telephone = client_for(make_user(role='hote', phone=None))
    apercu = sans_telephone.get(f'{C}hote/').data
    assert '[à compléter]' not in ' '.join(b['texte'] for b in apercu['blocs'])
    reponse = sans_telephone.post(f'{C}hote/signer/', {'nom': 'Ama Mensah', 'signature': _signature(), 'accepte': True,
                                                       'version': apercu['version']}, format='json')
    assert reponse.status_code == 400 and 'téléphone' in reponse.data['detail']


def test_admin_emet_un_contrat_et_la_partie_signe_par_lien(admin, client_for, make_user, societe, django_capture_on_commit_callbacks):
    chauffeur = _chauffeur()
    assert client_for(make_user()).post(A, {'type': 'chauffeur', 'partie_id': chauffeur.pk}, format='json').status_code == 403
    parties = admin.get(f'{A}parties/', {'type': 'chauffeur'}).data
    assert parties[0]['nom'] == 'Komi Adjo' and parties[0]['contrat'] is None

    with django_capture_on_commit_callbacks(execute=True):
        reponse = admin.post(A, {'type': 'chauffeur', 'partie_id': chauffeur.pk}, format='json')
    assert reponse.status_code == 201, reponse.data
    assert admin.post(A, {'type': 'chauffeur', 'partie_id': chauffeur.pk}, format='json').status_code == 409  # already ongoing
    jeton = _jeton(mail.outbox[-1])
    assert mail.outbox[-1].to == ['komi@exemple.tg']

    public = client_for(make_user()).__class__()  # client anonyme
    contrat = public.get(f'{C}signature/{jeton}/').data
    texte = ' '.join(b['texte'] for b in contrat['blocs'])
    assert 'TG 1234 AB' in texte and '20 %' in texte and contrat['statut'] == 'a_signer'
    assert public.get(f'{C}signature/faux-jeton/').status_code == 404
    _pdf(public.get(f'{C}signature/{jeton}/pdf/'))

    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        reponse = public.post(f'{C}signature/{jeton}/signer/', {'nom': 'Komi Adjo', 'signature': _signature(), 'accepte': True}, format='json')
    assert reponse.status_code == 200, reponse.data
    assert len(mail.outbox) == 2
    assert admin.get(A, {'statut': 'signe'}).data['count'] == 1
    _pdf(admin.get(f"{A}{ContratModel.objects.get().pk}/pdf/"))
    assert admin.get(f'{A}parties/', {'type': 'chauffeur'}).data[0]['contrat'] == 'signe'


def test_lien_expire_renvoi_et_annulation(admin, client_for, make_user, societe, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        contrat_id = admin.post(A, {'type': 'chauffeur', 'partie_id': _chauffeur().pk}, format='json').data['id']
    ancien = _jeton(mail.outbox[-1])
    ContratModel.objects.filter(pk=contrat_id).update(expire_le=timezone.now() - timedelta(days=1))
    public = client_for(make_user()).__class__()
    assert public.get(f'{C}signature/{ancien}/').data['expire'] is True
    signer = {'nom': 'Komi Adjo', 'signature': _signature(), 'accepte': True}
    assert public.post(f'{C}signature/{ancien}/signer/', signer, format='json').status_code == 400

    with django_capture_on_commit_callbacks(execute=True):
        assert admin.post(f'{A}{contrat_id}/renvoyer/').status_code == 200
    nouveau = _jeton(mail.outbox[-1])
    assert nouveau != ancien and public.get(f'{C}signature/{ancien}/').status_code == 404
    assert public.get(f'{C}signature/{nouveau}/').data['expire'] is False

    assert admin.post(f'{A}{contrat_id}/annuler/', {'motif': ''}, format='json').status_code == 400
    assert admin.post(f'{A}{contrat_id}/annuler/', {'motif': 'Chauffeur parti'}, format='json').data['statut'] == 'annule'
    assert public.get(f'{C}signature/{nouveau}/').status_code == 404


def test_modele_modifiable_et_versionne(admin, client_for, make_user, societe):
    modeles = admin.get(f'{A}modeles/').data
    assert {m['type'] for m in modeles['modeles']} == {'hote', 'hotel', 'loueur', 'chauffeur', 'ong'} and 'partie.nom' in modeles['variables']
    hote = make_user(role='hote')
    corps = ModeleContratModel.objects.get(type='hote').corps
    assert admin.put(f'{A}modeles/hote/', {'titre': 'Contrat Hôte', 'corps': corps + '\n\n{{ inconnue }}'}, format='json').status_code == 400
    reponse = admin.put(f'{A}modeles/hote/', {'titre': 'Contrat Hôte 2026', 'corps': corps + '\n\n## Annexe\nTexte ajouté.'}, format='json')
    assert reponse.status_code == 200 and reponse.data['version'] == 2
    apercu = client_for(hote).get(f'{C}hote/').data
    assert apercu['titre'] == 'Contrat Hôte 2026' and apercu['version'] == 2 and apercu['blocs'][-1]['texte'] == 'Texte ajouté.'


def test_contrat_hotel_emis_pour_un_compte_hote(admin, make_user, societe, django_capture_on_commit_callbacks):
    hotel = make_user(role='hote', email='reservations@hotel.tg')
    assert any(p['email'] == 'reservations@hotel.tg' for p in admin.get(f'{A}parties/', {'type': 'hotel'}).data)
    with django_capture_on_commit_callbacks(execute=True):
        reponse = admin.post(A, {'type': 'hotel', 'partie_id': hotel.pk}, format='json')
    assert reponse.status_code == 201, reponse.data
    contrat = ContratModel.objects.get(hote=hotel)
    assert contrat.type == 'hotel' and contrat.titre == 'Contrat hôtel et résidence hôtelière'
    assert "ci-après « l'Établissement »" in contrat.corps and '12 % du prix' in contrat.corps
    assert 'Charte du Réseau Kwa-Ba Partenaires' in contrat.corps and '{{' not in contrat.corps

def test_la_visite_attend_la_signature_du_contrat(client_for, make_user, make_hebergement, societe, django_capture_on_commit_callbacks):
    hote = make_user(role='hote')
    PieceIdentiteModel.objects.create(hote=hote, type_piece='cni', statut='verifiee')
    annonce = make_hebergement(host=hote, statut_verification='en_attente')
    make_user(role='agent', email='agent@kwa-ba.com')
    agent = client_for(make_user(role='agent'))
    assert agent.get('/api/v1/verifications/visites/').data['count'] == 0
    decision = agent.post(f'/api/v1/verifications/visites/{annonce.id}/decision/',
                          {'decision': 'validee', 'controles': json.dumps(TOUT_CONFORME)}, format='multipart')
    assert decision.status_code == 400 and 'contrat' in decision.data['detail']

    client = client_for(hote)
    version = client.get(f'{C}hote/').data['version']
    with django_capture_on_commit_callbacks(execute=True):
        client.post(f'{C}hote/signer/', {'nom': 'Test Hôte', 'signature': _signature(), 'accepte': True, 'version': version}, format='json')
    assert agent.get('/api/v1/verifications/visites/').data['count'] == 1
    assert any('Visite à planifier' in m.subject for m in mail.outbox)


def test_visites_inchangees_sans_informations_legales(client_for, make_user, make_hebergement):
    hote = make_user(role='hote')
    PieceIdentiteModel.objects.create(hote=hote, type_piece='cni', statut='verifiee')
    make_hebergement(host=hote, statut_verification='en_attente')
    assert client_for(make_user(role='agent')).get('/api/v1/verifications/visites/').data['count'] == 1


def test_signature_scannee_du_representant(admin, societe):
    image = Image.new('RGB', (800, 300), 'white')
    ImageDraw.Draw(image).line([(50, 250), (300, 60), (700, 200)], fill='black', width=8)
    tampon = BytesIO()
    image.save(tampon, 'JPEG')
    fichier = SimpleUploadedFile('signature.jpg', tampon.getvalue(), content_type='image/jpeg')
    reponse = admin.put('/api/v1/admin/documents/societe/', {'representant_nom': 'Mendé Fadel', 'signature_representant': fichier},
                        format='multipart')
    assert reponse.status_code == 200, reponse.data
    assert reponse.data['signature_presente'] is True
    png = admin.get('/api/v1/admin/documents/societe/signature/')
    assert png.status_code == 200 and png.content.startswith(b'\x89PNG')
    # The white background has become transparent
    assert Image.open(BytesIO(png.content)).getpixel((0, 0))[3] == 0
    assert admin.put('/api/v1/admin/documents/societe/', {'supprimer_signature': 'true'}, format='multipart').data['signature_presente'] is False
