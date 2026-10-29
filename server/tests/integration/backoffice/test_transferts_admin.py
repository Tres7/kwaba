"""Back-office: airport transfers (airports, fares, drivers, assignment, cancellation)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.securite.models import JournalAuditModel
from apps.transferts.models import AeroportModel, ChauffeurModel, TarifTransfertModel, TransfertModel

B = '/api/v1/admin/transferts/'


@pytest.fixture
def admin(make_user, client_for):
    return client_for(make_user(role='admin'))


def _chauffeur(categorie='berline', **extra):
    c = ChauffeurModel.objects.create(prenom='Komi', nom='Adjo', telephone='+22890000001', categorie=categorie,
                                      vehicule='Corolla grise', immatriculation='TG 1', pays_versement='TG',
                                      operateur_versement='togocel', numero_versement='90000001', **extra)
    c.aeroports.add('LFW')
    return c


@pytest.fixture
def transfert(make_user):
    return TransfertModel.objects.create(
        voyageur_id=make_user().pk, aeroport_id='LFW', arrivee=timezone.now() + timedelta(days=4), numero_vol='AF520',
        passagers=2, bagages=2, categorie='berline', destination='Villa Océane, Baguida', telephone='+33612345678',
        prix=15000, commission=3000, statut='confirme',
    )


def test_reserve_aux_admins(make_user, client_for):
    assert client_for(make_user(role='hote')).get(B + 'aeroports/').status_code == 403


def test_aeroport_et_tarifs(admin):
    reponse = admin.post(B + 'aeroports/', {'code': 'abj', 'nom': 'Félix-Houphouët-Boigny', 'ville': 'Abidjan',
                                            'pays': 'CI', 'fuseau': 'Africa/Abidjan'}, format='json')
    assert reponse.status_code == 201 and reponse.data['code'] == 'ABJ'
    assert admin.post(B + 'aeroports/', {'code': 'AB1', 'nom': 'x', 'ville': 'x', 'pays': 'CI', 'fuseau': 'x'},
                      format='json').status_code == 400
    tarifs = admin.put(f'{B}aeroports/ABJ/tarifs/', [{'categorie': 'berline', 'prix': 20000, 'actif': True},
                                                     {'categorie': 'van', 'prix': 35000, 'actif': False}], format='json')
    assert tarifs.status_code == 200 and len(tarifs.data['tarifs']) == 2
    admin.put(f'{B}aeroports/ABJ/tarifs/', [{'categorie': 'berline', 'prix': 22000, 'actif': True}], format='json')
    assert TarifTransfertModel.objects.get(aeroport_id='ABJ', categorie='berline').prix == 22000
    # The code cannot be changed
    admin.patch(f'{B}aeroports/ABJ/', {'code': 'XXX', 'actif': False}, format='json')
    assert AeroportModel.objects.filter(code='ABJ', actif=False).exists()
    assert JournalAuditModel.objects.filter(details__objet='tarifs_transfert').exists()


def test_chauffeur(admin):
    reponse = admin.post(B + 'chauffeurs/', {
        'prenom': 'Yao', 'nom': 'Mensah', 'telephone': '+22891000000', 'aeroports': ['LFW'], 'categorie': 'van',
        'vehicule': 'Hiace blanc', 'immatriculation': 'TG 9', 'pays_versement': 'TG', 'operateur_versement': 'moov_tg',
        'numero_versement': '91000000',
    }, format='json')
    assert reponse.status_code == 201, reponse.data
    assert admin.patch(f"{B}chauffeurs/{reponse.data['id']}/", {'operateur_versement': 'mtn_open'},
                       format='json').status_code == 400


def test_attribution_et_annulation(admin, transfert):
    bon = _chauffeur()
    trop_petit = ChauffeurModel.objects.create(prenom='A', nom='B', telephone='+22890000002', categorie='berline',
                                               vehicule='x', immatriculation='x', pays_versement='TG',
                                               operateur_versement='togocel', numero_versement='90000002')
    assert [c['id'] for c in admin.get(f'{B}transferts/{transfert.id}/chauffeurs/').data] == [bon.id]
    assert admin.post(f'{B}transferts/{transfert.id}/attribuer/', {'chauffeur': trop_petit.id},
                      format='json').status_code == 400
    reponse = admin.post(f'{B}transferts/{transfert.id}/attribuer/', {'chauffeur': bon.id}, format='json')
    assert reponse.status_code == 200 and reponse.data['statut'] == 'chauffeur_assigne'
    assert admin.get(B + 'transferts/', {'statut': 'chauffeur_assigne'}).data['count'] == 1

    annule = admin.post(f'{B}transferts/{transfert.id}/annuler/', {'motif': 'Vol annulé par la compagnie'}, format='json')
    assert annule.status_code == 200 and annule.data['statut'] == 'annule'
