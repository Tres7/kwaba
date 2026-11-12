"""Event of a paid stay for the traveller's calendar: an .ics file (RFC 5545) for the iPhone, Android and Outlook.

The hours are written in UTC: Togo is at UTC all year, without summer time. The event has the address and the landmark,
already shown to the traveller once the booking is paid, but never the host's phone (everything goes through the
Kwa-Ba messaging) nor the exact position of the listing (kept for the agents).
"""
from datetime import datetime, time
from urllib.parse import urlsplit

from django.conf import settings

from apps.export import api as export

# Hours of the listing when the booking has none (bookings made before the hours were frozen on them)
ARRIVEE_PAR_DEFAUT = time(14, 0)
DEPART_PAR_DEFAUT = time(11, 0)

TEXTES = {
    'fr': {
        'titre': 'Séjour · {nom}',
        'arrivee': 'Arrivée le {jour} à partir de {heure}',
        'depart': 'Départ le {jour} avant {heure}',
        'adresse': 'Adresse : {adresse}',
        'repere': 'Point de repère : {repere}',
        'voyageurs': 'Voyageurs : {nombre}',
        'reference': 'Réservation {reference}',
        'contact': "Pour joindre l'hôte : la messagerie Kwa-Ba.",
        'lien': 'Votre réservation : {url}',
        'rappel': 'Arrivée demain · {nom}',
        'pays': 'Togo',
    },
    'en': {
        'titre': 'Stay · {nom}',
        'arrivee': 'Arrival on {jour} from {heure}',
        'depart': 'Departure on {jour} before {heure}',
        'adresse': 'Address: {adresse}',
        'repere': 'Landmark: {repere}',
        'voyageurs': 'Guests: {nombre}',
        'reference': 'Booking {reference}',
        'contact': 'To reach the host: the Kwa-Ba messaging.',
        'lien': 'Your booking: {url}',
        'rappel': 'Arrival tomorrow · {nom}',
        'pays': 'Togo',
    },
}


def _jour(jour, langue: str) -> str:
    return jour.strftime('%d/%m/%Y') if langue == 'fr' else jour.strftime('%Y-%m-%d')


def _heure(heure: time, langue: str) -> str:
    return heure.strftime('%H h %M').replace(' 00', '') if langue == 'fr' else heure.strftime('%H:%M')


def nom_fichier(reservation) -> str:
    return f"kwa-ba-{reservation.reference}.ics"


def evenement(reservation, annonce: dict, langue: str = 'fr') -> str:
    """Contents of the .ics file of a paid stay, from the arrival to the departure, with a reminder the day before."""
    t = TEXTES['en' if langue == 'en' else 'fr']
    arrivee = reservation.arrivee_a_partir or ARRIVEE_PAR_DEFAUT
    depart = reservation.depart_avant or DEPART_PAR_DEFAUT
    adresse = ', '.join(x for x in (annonce.get('location'), annonce.get('city'), t['pays']) if x)
    url = f"{settings.FRONTEND_URL.rstrip('/')}{'/en' if langue == 'en' else ''}/profil/reservations"
    description = [
        t['arrivee'].format(jour=_jour(reservation.check_in, langue), heure=_heure(arrivee, langue)),
        t['depart'].format(jour=_jour(reservation.check_out, langue), heure=_heure(depart, langue)),
        t['adresse'].format(adresse=adresse),
        *([t['repere'].format(repere=annonce['point_repere'])] if annonce.get('point_repere') else []),
        t['voyageurs'].format(nombre=reservation.guests_count),
        t['reference'].format(reference=reservation.reference),
        t['contact'],
        t['lien'].format(url=url),
    ]
    domaine = urlsplit(settings.FRONTEND_URL).hostname or 'kwa-ba.com'
    name = annonce.get('name') or 'Kwa-Ba'
    return export.calendar([export.Event(
        uid=f'reservation-{reservation.pk}@{domaine}',
        start=datetime.combine(reservation.check_in, arrivee),
        end=datetime.combine(reservation.check_out, depart),
        title=t['titre'].format(nom=name),
        location=adresse,
        description='\n'.join(description),
        url=url,
        alarm='-P1D',
        alarm_text=t['rappel'].format(nom=name),
    )], prodid='-//Kwa-Ba//Reservations//FR')
