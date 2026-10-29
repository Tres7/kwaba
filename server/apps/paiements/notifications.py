"""Money-related emails, sent by the worker (never during a web request).

Each row carries a `notifie` flag: a failed sending (SMTP unavailable) is retried
at the next pass, and an email is never sent twice.
"""
import logging
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from apps.notifications.infrastructure.email.envoi import send_mail
from django.template.loader import render_to_string
from django.utils import formats

from . import tarifs
from .models import PaiementModel, ProfilVersementModel, RemboursementModel, VersementModel
from .operateurs import PAYS, nom_operateur

logger = logging.getLogger('apps.paiements.notifications')


def _fcfa(montant: int) -> str:
    return f"{montant:,}".replace(',', ' ') + ' FCFA'


def _date(valeur) -> str:
    return formats.date_format(valeur, 'j F Y')


def _envoyer(gabarit: str, sujet: str, destinataires: list[str], contexte: dict, pieces_jointes=None):
    # Test SMTPs (Mailtrap) and some providers limit the number of emails per second
    time.sleep(settings.PAIEMENTS_PAUSE_EMAIL)
    send_mail(
        subject=sujet,
        # `gabarit`: name in emails/paiements/, or full path (other modules, e.g. transfers)
        message=render_to_string(gabarit if '/' in gabarit else f'emails/paiements/{gabarit}.txt', contexte),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinataires,
        pieces_jointes=pieces_jointes,
    )


TYPES_OBJETS = {'ReservationModel': 'reservation', 'TransfertModel': 'transfert', 'LocationModel': 'location',
                'DonModel': 'don'}


def _pieces(type_objet: str, objet_id):
    """PDF voucher and receipt attached to the confirmation email."""
    from apps.documents.api import pieces_confirmation  # local import: documents depends on paiements
    return pieces_confirmation(type_objet, objet_id)


def _documents(objet):
    return _pieces(TYPES_OBJETS[type(objet).__name__], objet.pk)


def _admins() -> list[str]:
    return list(get_user_model().objects.filter(role='admin', is_active=True).values_list('email', flat=True))


def _sejour(r) -> dict:
    annonce = tarifs._annonce(r)
    return {
        'hebergement': annonce['name'], 'ville': annonce['city'], 'reference': r.reference,
        'arrivee': _date(r.check_in), 'depart': _date(r.check_out), 'voyageurs': r.guests_count,
    }


def _reservation(reservation_id):
    """The booking as a plain object (reservations.api), for the emails about its money."""
    from apps.reservations import api as reservations  # local import: reservations depends on paiements

    return reservations.objet(reservation_id)


def reservation_payee_voyageur(paiement: PaiementModel):
    r = _reservation(paiement.reservation_id)
    voyageur = r.guest
    _envoyer('reservation_payee_voyageur', f"Séjour confirmé : {tarifs._annonce(r)['name']}", [voyageur.email], {
        **_sejour(r), 'prenom': voyageur.first_name, 'montant': _fcfa(paiement.montant),
        'url': f"{settings.FRONTEND_URL}/reservation/confirmation/{r.id}",
        'url_remboursement': f"{settings.FRONTEND_URL}/remboursement",
        'politique': tarifs.texte_politique(r),
    }, pieces_jointes=_pieces('reservation', r.id))


def reservation_payee_hote(paiement: PaiementModel):
    r = _reservation(paiement.reservation_id)
    annonce = tarifs._annonce(r)
    voyageur, hote = r.guest, get_user_model().objects.get(pk=annonce['host_id'])
    montants = tarifs.montants_de(r)
    _envoyer('reservation_payee_hote', f"Nouvelle réservation payée : {annonce['name']}", [hote.email], {
        **_sejour(r), 'prenom': hote.first_name, 'voyageur': f"{voyageur.first_name} {voyageur.last_name}".strip(),
        'message': r.message, 'montant_hote': _fcfa(montants.montant_hote),
        'date_versement': _date(tarifs.date_versement(r)),
        'profil_complet': ProfilVersementModel.objects.filter(hote=hote).exists(),
        'url_revenus': f"{settings.FRONTEND_URL}/hote/espace?onglet=revenus",
        'url_reservations': f"{settings.FRONTEND_URL}/hote/espace?onglet=reservations",
    })


def versement_envoye(v: VersementModel):
    r = _reservation(v.reservation_id)
    indicatif = next((p['indicatif'] for p in PAYS.values() if any(c == v.mode for c, _ in p['operateurs'])), '')
    _envoyer('versement_envoye', f"Versement de {_fcfa(v.montant)} envoyé", [v.hote.email], {
        'prenom': v.hote.first_name, 'montant': _fcfa(v.montant), 'montant_brut': _fcfa(v.montant_brut),
        'commission': _fcfa(v.commission), 'operateur': nom_operateur(v.mode),
        'numero': f"+{indicatif} {v.numero}" if indicatif else v.numero,
        'voyageur': r.guest.first_name, 'hebergement': tarifs._annonce(r)['name'], 'reference': r.reference,
        'url_revenus': f"{settings.FRONTEND_URL}/hote/espace?onglet=revenus",
    })


def remboursement_envoye(rb: RemboursementModel):
    if rb.paiement.prestataire == 'paypal':
        destination = 'votre compte PayPal'
    elif rb.numero:
        destination = f"votre compte {nom_operateur(rb.operateur)} (+{PAYS[rb.pays]['indicatif']} {rb.numero})"
    else:
        destination = ''
    _envoyer('remboursement_envoye', f"Remboursement de {_fcfa(rb.montant)} envoyé", [rb.payeur.email], {
        'prenom': rb.payeur.first_name, 'montant': _fcfa(rb.montant), 'reference': rb.reference,
        'hebergement': rb.libelle, 'destination': destination,
    })


def alerte_admin(type_: str, ligne, beneficiaire: str, *, reference: str, libelle: str, section: str = 'paiements'):
    destinataires = _admins()
    if not destinataires:
        logger.error("%s à traiter (%s) mais aucun administrateur à prévenir", type_, ligne.pk)
        return
    _envoyer('alerte_admin', f"[Kwa-Ba] {type_} à traiter : {reference}", destinataires, {
        'type': type_, 'reference': reference, 'hebergement': libelle, 'montant': _fcfa(ligne.montant),
        'beneficiaire': beneficiaire, 'erreur': ligne.derniere_erreur or '-',
        'url_admin': f"{settings.BACKEND_URL}/admin/{section}/",
    })


def _traiter(qs, fonction, drapeau='notifie'):
    envoyes = 0
    for ligne in qs[:50]:
        try:
            fonction(ligne)
        except Exception:
            logger.exception("Email non envoyé pour %s %s (nouvel essai à la prochaine passe)", type(ligne).__name__, ligne.pk)
            continue
        type(ligne).objects.filter(pk=ligne.pk).update(**{drapeau: True})
        envoyes += 1
    return envoyes


def envoyer_notifications() -> int:
    from apps.reservations import api as reservations  # local import: reservations depends on paiements

    a_notifier = (PaiementModel.objects.filter(statut='reussi', reservation_id__isnull=False)
                  .filter(Q(notifie=False) | Q(notifie_hote=False)).values_list('reservation_id', flat=True))
    payes = PaiementModel.objects.filter(statut='reussi', reservation_id__in=reservations.ids_confirmees(a_notifier))
    total = _traiter(payes.filter(notifie=False), reservation_payee_voyageur)
    total += _traiter(payes.filter(notifie_hote=False), reservation_payee_hote, drapeau='notifie_hote')
    total += _traiter(
        VersementModel.objects.filter(statut='envoye', notifie=False).select_related('hote'),
        versement_envoye,
    )
    total += _traiter(
        VersementModel.objects.filter(statut='echoue', notifie=False).select_related('hote'),
        lambda v: alerte_admin('Versement à un hôte', v, f"{v.hote.email} ({nom_operateur(v.mode)} {v.numero})",
                               reference=_reservation(v.reservation_id).reference,
                               libelle=tarifs._annonce(_reservation(v.reservation_id))['name']),
    )
    total += _traiter(
        RemboursementModel.objects.filter(statut='envoye', notifie=False).select_related('paiement'),
        remboursement_envoye,
    )
    total += _traiter(
        RemboursementModel.objects.filter(statut='a_traiter', notifie=False).select_related('paiement'),
        lambda rb: alerte_admin('Remboursement', rb, rb.payeur.email, reference=rb.reference, libelle=rb.libelle),
    )
    return total
