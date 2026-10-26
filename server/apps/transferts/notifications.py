"""Transfer emails, sent by the worker (same principle as apps.paiements.notifications)."""
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import formats, timezone

from apps.paiements.notifications import _admins, _documents, _envoyer, _fcfa, alerte_admin

from . import tarifs
from .models import TransfertModel, VersementChauffeurModel

logger = logging.getLogger('apps.transferts.notifications')


def _heure(t: TransfertModel) -> str:
    return formats.date_format(t.arrivee.astimezone(ZoneInfo(t.aeroport.fuseau)), 'l j F Y à H\\hi')


def _course(t: TransfertModel) -> dict:
    return {
        'reference': t.reference, 'aeroport': f"{t.aeroport.nom} ({t.aeroport.code})", 'arrivee': _heure(t),
        'vol': t.numero_vol, 'destination': t.destination, 'passagers': t.passagers, 'bagages': t.bagages,
        'vehicule': tarifs.CATEGORIES[t.categorie]['nom'], 'attente': tarifs.ATTENTE_INCLUSE_MINUTES,
        'voyageur': f"{t.voyageur.first_name} {t.voyageur.last_name}".strip(), 'telephone_voyageur': t.telephone,
        'url': f"{settings.FRONTEND_URL}/transfert/{t.id}",
    }


def confirme(t: TransfertModel):
    _envoyer('emails/transferts/transfert_confirme.txt', f"Transfert confirmé : {t.aeroport.ville}", [t.voyageur.email], {
        **_course(t), 'prenom': t.voyageur.first_name, 'montant': _fcfa(t.prix),
    }, pieces_jointes=_documents(t))


def a_attribuer(t: TransfertModel, urgent: bool = False):
    destinataires = _admins()
    if not destinataires:
        logger.error("Transfert %s à attribuer mais aucun administrateur à prévenir", t.reference)
        return
    from .services import chauffeurs_disponibles

    sujet = f"[Kwa-Ba] {'URGENT : ' if urgent else ''}Chauffeur à attribuer : {t.reference}"
    _envoyer('emails/transferts/a_attribuer.txt', sujet, destinataires, {
        **_course(t), 'urgent': urgent, 'nb_chauffeurs': chauffeurs_disponibles(t).count(),
        'url_admin': f"{settings.BACKEND_URL}/admin/transferts/transfertmodel/{t.id}/change/",
    })


def chauffeur_au_voyageur(t: TransfertModel):
    c = t.chauffeur
    _envoyer('emails/transferts/chauffeur_assigne.txt', f"Votre chauffeur à {t.aeroport.ville}", [t.voyageur.email], {
        **_course(t), 'prenom': t.voyageur.first_name, 'chauffeur': f"{c.prenom} {c.nom}",
        'telephone_chauffeur': c.telephone, 'vehicule': c.vehicule, 'immatriculation': c.immatriculation,
        'assistance': settings.ASSISTANCE_CONTACT,
    })


def course_au_chauffeur(t: TransfertModel):
    c = t.chauffeur
    if not c.email:
        return  # driver told by phone by the team
    _envoyer('emails/transferts/course_chauffeur.txt', f"Nouvelle course Kwa-Ba : {_heure(t)}", [c.email], {
        **_course(t), 'prenom': c.prenom, 'message': t.message, 'montant': _fcfa(t.montant_chauffeur),
    })


def versement_au_chauffeur(v: VersementChauffeurModel):
    c, t = v.chauffeur, v.transfert
    if not c.email:
        return
    _envoyer('emails/transferts/versement_chauffeur.txt', f"Versement de {_fcfa(v.montant)} envoyé", [c.email], {
        'prenom': c.prenom, 'reference': t.reference, 'aeroport': t.aeroport.ville, 'arrivee': _heure(t),
        'montant': _fcfa(v.montant), 'montant_brut': _fcfa(v.montant_brut), 'commission': _fcfa(v.commission),
    })


def _traiter(qs, fonction, drapeau):
    envoyes = 0
    for ligne in qs[:50]:
        try:
            fonction(ligne)
        except Exception:
            logger.exception("Email non envoyé pour %s (nouvel essai à la prochaine passe)", ligne.pk)
            continue
        type(ligne).objects.filter(pk=ligne.pk).update(**{drapeau: True})
        envoyes += 1
    return envoyes


def envoyer_notifications() -> int:
    qs = TransfertModel.objects.select_related('voyageur', 'aeroport', 'chauffeur')
    payes = qs.filter(statut__in=('confirme', 'chauffeur_assigne'))
    total = _traiter(payes.filter(confirmation_notifiee=False), confirme, 'confirmation_notifiee')
    total += _traiter(payes.filter(admins_notifies=False), a_attribuer, 'admins_notifies')
    total += _traiter(
        qs.filter(statut='confirme', alerte_sans_chauffeur=False, arrivee__lte=timezone.now() + timedelta(hours=24)),
        lambda t: a_attribuer(t, urgent=True), 'alerte_sans_chauffeur',
    )
    assignes = qs.filter(statut='chauffeur_assigne')
    total += _traiter(assignes.filter(chauffeur_notifie=False), chauffeur_au_voyageur, 'chauffeur_notifie')
    total += _traiter(assignes.filter(course_envoyee_chauffeur=False), course_au_chauffeur, 'course_envoyee_chauffeur')

    versements = VersementChauffeurModel.objects.select_related('chauffeur', 'transfert__aeroport')
    total += _traiter(versements.filter(statut='envoye', notifie=False), versement_au_chauffeur, 'notifie')
    total += _traiter(
        versements.filter(statut='echoue', notifie=False),
        lambda v: alerte_admin(
            'Versement à un chauffeur', v, f"{v.chauffeur} ({v.mode} {v.numero})",
            reference=v.transfert.reference, libelle=f"Transfert {v.transfert.aeroport.ville}", section='transferts',
        ),
        'notifie',
    )
    return total
