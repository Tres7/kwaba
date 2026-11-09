"""Photos added by the host to a verified listing: online at once, checked afterwards by an agent from a distance.
Removing a photo the agent saw, or moving the address, still takes the listing back to a full verification."""
import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from apps.hebergements.models import HebergementModel

HEBERGEMENTS = '/api/v1/hebergements/'
COMPTEURS = '/api/v1/verifications/compteurs/'
VUES = [f'https://images.unsplash.com/vue-{n}.jpg' for n in range(5)]
F, G = 'https://images.unsplash.com/ajout-f.jpg', 'https://images.unsplash.com/ajout-g.jpg'


@pytest.fixture
def annonce(make_hebergement):
    """A listing verified by an agent, with the 5 photos they saw."""
    return make_hebergement(image_url=VUES[0], images=VUES, legendes_photos={u: 'salon' for u in VUES})


@pytest.fixture
def hote(client_for, annonce):
    return client_for(get_user_model().objects.get(pk=annonce.host_id))


def _modifier(hote, annonce, images, **extra):
    reponse = hote.patch(f'{HEBERGEMENTS}{annonce.id}/', {
        'images': images, 'legendes_photos': {u: 'salle_de_sport' if u in (F, G) else 'salon' for u in images}, **extra,
    }, format='json')
    assert reponse.status_code == 200, reponse.data
    annonce.refresh_from_db()
    return annonce


def _decider(client, annonce, retirer, motif=''):
    return client.post(f'/api/v1/verifications/photos/{annonce.id}/decision/', {'retirer': retirer, 'motif': motif},
                       format='json')


def test_ajouter_des_photos_garde_l_annonce_en_ligne(hote, annonce, api_client, client_for, make_user,
                                                     django_capture_on_commit_callbacks):
    agent = make_user(role='agent')
    with django_capture_on_commit_callbacks(execute=True):
        _modifier(hote, annonce, [*VUES, F, G])

    assert annonce.statut_verification == 'verifiee' and annonce.photos_a_controler == [F, G]
    assert [h['id'] for h in api_client.get(HEBERGEMENTS).data['results']] == [str(annonce.id)]  # still online
    assert any('Photos à contrôler' in m.subject for m in mail.outbox if agent.email in m.to)
    assert client_for(agent).get(COMPTEURS).data['photos'] == 1


def test_retirer_une_photo_vue_par_l_agent_remet_en_verification(hote, annonce):
    _modifier(hote, annonce, [*VUES[1:], F])
    assert annonce.statut_verification == 'en_attente' and annonce.photos_a_controler is None


def test_changer_l_adresse_remet_en_verification(hote, annonce):
    _modifier(hote, annonce, [*VUES, F], location='Agbalépédo, rue 12')
    assert annonce.statut_verification == 'en_attente'


def test_l_hote_retire_une_photo_pas_encore_controlee(hote, annonce):
    _modifier(hote, annonce, [*VUES, F, G])
    _modifier(hote, annonce, [*VUES, F])
    assert annonce.statut_verification == 'verifiee' and annonce.photos_a_controler == [F]


def test_l_agent_retire_une_photo_ajoutee_et_l_hote_est_prevenu(hote, annonce, client_for, make_user,
                                                                 django_capture_on_commit_callbacks):
    _modifier(hote, annonce, [*VUES, F, G])
    agent = client_for(make_user(role='agent'))
    assert _decider(agent, annonce, [G]).status_code == 400  # a reason is needed to remove

    with django_capture_on_commit_callbacks(execute=True):
        reponse = _decider(agent, annonce, [G], motif="Cette photo montre un autre logement.")
    assert reponse.status_code == 200, reponse.data
    annonce.refresh_from_db()
    assert annonce.images == [*VUES, F] and G not in annonce.legendes_photos and annonce.photos_a_controler is None
    message = next(m for m in mail.outbox if 'Photos retirées' in m.subject)
    assert 'autre logement' in message.body
    assert agent.get(COMPTEURS).data['photos'] == 0


def test_l_agent_garde_toutes_les_photos(hote, annonce, client_for, make_user):
    _modifier(hote, annonce, [*VUES, F, G])
    assert _decider(client_for(make_user(role='agent')), annonce, []).status_code == 200
    annonce.refresh_from_db()
    assert annonce.images == [*VUES, F, G] and annonce.photos_a_controler is None


def test_personne_ne_controle_les_photos_de_sa_propre_annonce(hote, annonce, client_for):
    _modifier(hote, annonce, [*VUES, F])
    get_user_model().objects.filter(pk=annonce.host_id).update(role='agent')  # a former host who became an agent
    devenu_agent = client_for(get_user_model().objects.get(pk=annonce.host_id))
    assert _decider(devenu_agent, annonce, []).status_code == 400
    assert HebergementModel.objects.get(pk=annonce.pk).photos_a_controler == [F]


def test_un_voyageur_ne_controle_pas(hote, annonce, client_for, make_user):
    _modifier(hote, annonce, [*VUES, F])
    assert _decider(client_for(make_user()), annonce, []).status_code == 403
