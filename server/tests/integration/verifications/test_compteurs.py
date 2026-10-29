"""Counters of the back-office and agent space badges: identity documents to check and listings to visit."""
import pytest

from apps.verifications.models import PieceIdentiteModel

COMPTEURS = '/api/v1/verifications/compteurs/'
ADMIN_ANNONCES = '/api/v1/admin/hebergements/'


def _piece(hote, statut):
    return PieceIdentiteModel.objects.create(hote_id=hote.pk, type_piece='cni', statut=statut)


def test_counts_what_waits_for_an_agent(client_for, make_user, make_hebergement):
    soumise = make_user(role='hote', phone='+22890000011')
    _piece(soumise, 'soumise')
    _piece(make_user(role='hote', phone='+22890000012'), 'refusee')
    verifie = make_user(role='hote', phone='+22890000013')
    _piece(verifie, 'verifiee')
    make_hebergement(host=verifie, statut_verification='en_attente')    # ready for a visit
    make_hebergement(host=verifie, statut_verification='refusee')       # waits for the host
    make_hebergement(host=soumise, statut_verification='en_attente')    # identity not checked yet: no visit

    for role in ('agent', 'admin'):
        assert client_for(make_user(role=role)).get(COMPTEURS).data == {'pieces': 1, 'visites': 1, 'total': 2}


@pytest.mark.parametrize('role', ['voyageur', 'hote'])
def test_counters_are_for_agents_and_admins_only(client_for, make_user, api_client, role):
    assert client_for(make_user(role=role)).get(COMPTEURS).status_code == 403
    assert api_client.get(COMPTEURS).status_code == 401


def test_back_office_filters_listings_by_verification_status(client_for, make_user, make_hebergement):
    make_hebergement(name='En attente', statut_verification='en_attente')
    make_hebergement(name='Refusée', statut_verification='refusee')
    make_hebergement(name='Vérifiée')
    admin = client_for(make_user(role='admin'))

    noms = [h['name'] for h in admin.get(ADMIN_ANNONCES, {'statut': 'en_attente'}).data['results']]
    assert noms == ['En attente']
    assert admin.get(ADMIN_ANNONCES, {'statut': 'inconnu'}).data['count'] == 3  # unknown value: no filter
