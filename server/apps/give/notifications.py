"""Kwa-Ba Give emails, sent by the worker (same principle as apps.paiements.notifications)."""
import logging

from django.conf import settings
from django.utils import formats, timezone

from apps.paiements.notifications import _admins, _documents, _envoyer, _fcfa

from . import montants
from .models import DonModel, ReversementModel

logger = logging.getLogger('apps.give.notifications')


def _mois(periode) -> str:
    return formats.date_format(periode, 'F Y')


def recu(don: DonModel):
    o = don.organisation
    _envoyer('emails/give/recu_don.txt', f"Merci pour votre don à {o.nom}", [don.donateur.email], {
        'prenom': don.donateur.first_name, 'organisation': o.nom, 'projet': don.projet.titre if don.projet else '',
        'reference': don.reference, 'date': formats.date_format(don.paye_le, 'j F Y'),
        'montant': _fcfa(don.montant), 'total': _fcfa(don.total), 'frais': _fcfa(don.frais),
        'montant_ong': _fcfa(don.montant_ong), 'couvre_frais': don.couvre_frais,
        'date_reversement': formats.date_format(montants.date_reversement(timezone.localtime(don.paye_le).date()), 'j F Y'),
        'url': f"{settings.FRONTEND_URL}/profil/dons",
    }, pieces_jointes=_documents(don))


def reversement_a_effectuer(r: ReversementModel):
    destinataires = _admins()
    if not destinataires:
        logger.error("Reversement %s à effectuer mais aucun administrateur à prévenir", r.reference)
        return
    _envoyer('emails/give/reversement_a_effectuer.txt', f"[Kwa-Ba Give] Reversement à effectuer : {r.organisation.nom}",
             destinataires, {
                 'organisation': r.organisation.nom, 'mois': _mois(r.periode), 'montant': _fcfa(r.montant),
                 'nb_dons': r.nb_dons, 'date_prevue': formats.date_format(r.date_prevue, 'j F Y'),
                 'reference': r.reference, 'url_admin': f"{settings.BACKEND_URL}/admin/give/reversementmodel/{r.pk}/change/",
             })


def don_reverse(don: DonModel):
    r = don.reversement
    _envoyer('emails/give/don_reverse.txt', f"Votre don a été reversé à {r.organisation.nom}", [don.donateur.email], {
        'prenom': don.donateur.first_name, 'organisation': r.organisation.nom, 'reference': don.reference,
        'montant_ong': _fcfa(don.montant_ong), 'mois': _mois(r.periode), 'total': _fcfa(r.montant),
        'nb_dons': r.nb_dons, 'date': formats.date_format(r.effectue_le, 'j F Y'), 'note': r.note,
        'url': f"{settings.FRONTEND_URL}/give/{r.organisation.slug}#reversements",
    })


def _traiter(qs, fonction, drapeau):
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
    relations = ('donateur', 'organisation', 'projet')
    total = _traiter(DonModel.objects.filter(statut='paye', recu_envoye=False).select_related(*relations), recu, 'recu_envoye')
    total += _traiter(
        ReversementModel.objects.filter(statut='a_effectuer', admins_notifies=False, nb_dons__gt=0).select_related('organisation'),
        reversement_a_effectuer, 'admins_notifies',
    )
    total += _traiter(
        DonModel.objects.filter(reversement__statut='effectue', reversement_notifie=False)
        .select_related('donateur', 'reversement__organisation'),
        don_reverse, 'reversement_notifie',
    )
    return total
