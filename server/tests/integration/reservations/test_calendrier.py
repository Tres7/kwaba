"""Paid stay in the traveller's phone calendar: .ics file (RFC 5545)."""
from datetime import time

import pytest

from apps.reservations.calendrier import _plier


def _url(reservation, langue=''):
    return f'/api/v1/reservations/{reservation.pk}/calendrier/' + (f'?langue={langue}' if langue else '')


def _deplier(contenu: str) -> str:
    """Lines as they read once unfolded (a line break followed by a space continues the line)."""
    return contenu.replace('\r\n ', '')


@pytest.fixture
def sejour(make_hebergement, make_reservation, make_user, settings):
    settings.FRONTEND_URL = 'https://kwa-ba.com'
    voyageur = make_user()
    annonce = make_hebergement(name='Villa Akwaba, vue mer', city='Lomé', location='Bè Kpota',
                               point_repere='Derrière la pharmacie Bon Secours; portail bleu')
    reservation = make_reservation(annonce, guest=voyageur, starts_in=20, nights=3)
    reservation.arrivee_a_partir, reservation.depart_avant, reservation.guests_count = time(15, 0), time(10, 30), 2
    reservation.save(update_fields=['arrivee_a_partir', 'depart_avant', 'guests_count'])
    return voyageur, reservation


def test_evenement_du_sejour(sejour, client_for):
    voyageur, reservation = sejour
    reponse = client_for(voyageur).get(_url(reservation))
    assert reponse.status_code == 200
    assert reponse['Content-Type'] == 'text/calendar; charset=utf-8'
    assert reponse['Content-Disposition'] == f'attachment; filename="kwa-ba-{reservation.reference}.ics"'
    assert reponse['Cache-Control'] == 'private, no-store'
    contenu = reponse.content.decode('utf-8')
    lignes = _deplier(contenu).split('\r\n')
    assert lignes[0] == 'BEGIN:VCALENDAR' and lignes[-2] == 'END:VCALENDAR' and contenu.endswith('\r\n')
    # Hours frozen on the booking, in UTC (Togo is at UTC all year)
    assert f"DTSTART:{reservation.check_in.strftime('%Y%m%d')}T150000Z" in lignes
    assert f"DTEND:{reservation.check_out.strftime('%Y%m%d')}T103000Z" in lignes
    assert f'UID:reservation-{reservation.pk}@kwa-ba.com' in lignes
    assert 'URL:https://kwa-ba.com/profil/reservations' in lignes
    # Commas and semicolons escaped
    assert 'SUMMARY:Séjour · Villa Akwaba\\, vue mer' in lignes
    assert 'LOCATION:Bè Kpota\\, Lomé\\, Togo' in lignes
    description, = [ligne for ligne in lignes if ligne.startswith('DESCRIPTION:Arrivée le')]
    assert 'Point de repère : Derrière la pharmacie Bon Secours\\; portail bleu' in description
    assert 'à partir de 15 h' in description and 'avant 10 h 30' in description and 'Voyageurs : 2' in description
    assert reservation.reference in description and 'messagerie Kwa-Ba' in description
    assert 'TRIGGER:-P1D' in lignes


def test_jamais_le_telephone_ni_la_position(sejour, client_for):
    voyageur, reservation = sejour
    contenu = client_for(voyageur).get(_url(reservation)).content.decode('utf-8')
    hote_telephone = '+22991'
    assert hote_telephone not in contenu
    assert 'GEO:' not in contenu


def test_en_anglais(sejour, client_for):
    voyageur, reservation = sejour
    lignes = _deplier(client_for(voyageur).get(_url(reservation, 'en')).content.decode('utf-8')).split('\r\n')
    assert 'SUMMARY:Stay · Villa Akwaba\\, vue mer' in lignes
    assert 'URL:https://kwa-ba.com/en/profil/reservations' in lignes
    assert any(ligne.startswith('DESCRIPTION:Arrival on') and 'from 15:00' in ligne and 'Landmark: ' in ligne
               for ligne in lignes)


def test_lignes_de_75_octets_au_plus(sejour, client_for):
    voyageur, reservation = sejour
    contenu = client_for(voyageur).get(_url(reservation)).content.decode('utf-8')
    assert all(len(ligne.encode('utf-8')) <= 75 for ligne in contenu.split('\r\n'))


def test_pliage_jamais_dans_une_lettre_accentuee():
    lignes = _plier('DESCRIPTION:' + 'é' * 60).split('\r\n')
    assert [len(ligne.encode('utf-8')) for ligne in lignes] == [74, 59]
    assert ''.join(lignes[:1] + [ligne[1:] for ligne in lignes[1:]]) == 'DESCRIPTION:' + 'é' * 60


def test_seulement_le_voyageur_et_seulement_paye(sejour, client_for, make_user, make_reservation, api_client):
    voyageur, reservation = sejour
    assert api_client.get(_url(reservation)).status_code == 401
    assert client_for(make_user()).get(_url(reservation)).status_code == 404
    # Not paid yet, or cancelled: no address yet (or any more)
    for statut in ('pending', 'cancelled'):
        reservation.status = statut
        reservation.save(update_fields=['status'])
        assert client_for(voyageur).get(_url(reservation)).status_code == 404


def test_heures_par_defaut(make_hebergement, make_reservation, make_user, client_for):
    voyageur = make_user()
    reservation = make_reservation(make_hebergement(), guest=voyageur)
    lignes = _deplier(client_for(voyageur).get(_url(reservation)).content.decode('utf-8')).split('\r\n')
    # A booking made before the hours were frozen on it: those of the listing by default
    assert f"DTSTART:{reservation.check_in.strftime('%Y%m%d')}T140000Z" in lignes
    assert f"DTEND:{reservation.check_out.strftime('%Y%m%d')}T110000Z" in lignes
