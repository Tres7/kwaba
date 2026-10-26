"""Verification of hosts and listings, in this order:

1. the host sends their identity document, checked remotely by an agent or an admin;
2. only once the identity is verified, their listings are offered to the agents for a visit;
3. the agent visits the listing and publishes (or refuses) it.

No travel is therefore asked for a host whose identity has not been checked.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.notifications.infrastructure.email.envoi import send_mail

from .fichiers import image_normalisee
from .models import PhotoVisiteModel, PieceIdentiteModel, VisiteModel

logger = logging.getLogger('apps.verifications')

ROLES_VERIFICATEURS = ('agent', 'admin')
MAX_PHOTOS_VISITE = 10
# Unverified listings a host may have while their identity is not verified (against abuse)
MAX_ANNONCES_HOTE_NON_VERIFIE = 3


class VerificationErreur(Exception):
    """Message that can be shown to the agent."""


def _envoyer(gabarit: str, sujet: str, destinataires: list[str], contexte: dict) -> None:
    """After the transaction is committed; a sending failure never cancels the verification."""
    def envoyer():
        try:
            send_mail(sujet, render_to_string(f'emails/verifications/{gabarit}.txt', contexte),
                      settings.DEFAULT_FROM_EMAIL, destinataires)
        except Exception:
            logger.exception("Email %s non envoyé", gabarit)

    if destinataires:
        transaction.on_commit(envoyer)


def _verificateurs() -> list[str]:
    return list(get_user_model().objects.filter(role__in=ROLES_VERIFICATEURS, is_active=True)
                .values_list('email', flat=True))


def contrats_disponibles() -> bool:
    """The host agreement becomes required as soon as Kwa-Ba is registered (RCCM and NIF filled in)."""
    from apps.documents.models import ParametresSocieteModel

    return ParametresSocieteModel.courants().immatriculee


def contrat_manquant(hote) -> bool:
    from apps.contrats.services import hote_a_signe

    return contrats_disponibles() and not hote_a_signe(hote)


def pieces_a_controler():
    """Identity documents sent by hosts and not checked yet, oldest first (agent space and counters)."""
    return PieceIdentiteModel.objects.filter(statut='soumise').order_by('soumise_le')


def annonces_a_visiter():
    """Listings an agent can visit now, oldest first: waiting, host identity verified, and host agreement signed once
    it is required. Same list in the agent space and in the counters."""
    from apps.hebergements.models import HebergementModel  # local import, as in the rest of this module

    qs = HebergementModel.objects.filter(statut_verification='en_attente', host__piece_identite__statut='verifiee')
    if contrats_disponibles():
        qs = qs.filter(host__contrats__type__in=('hote', 'hotel'), host__contrats__statut='signe')
    return qs.order_by('created_at')


def statut_piece(hote) -> str:
    piece = PieceIdentiteModel.objects.filter(hote=hote).first()
    return piece.statut if piece else 'absente'


def identite_verifiee(hote) -> bool:
    return PieceIdentiteModel.objects.filter(hote=hote, statut='verifiee').exists()


def verifier_limite_annonces(hote) -> None:
    """Before a new listing: phone required (the agent must be able to reach the host), and no more than
    MAX_ANNONCES_HOTE_NON_VERIFIE pending listings while the identity is not verified."""
    from apps.hebergements.models import HebergementModel  # local import: hebergements imports this module

    if hote.role == 'admin':
        return
    if not hote.phone:
        raise VerificationErreur(
            "Ajoutez votre numéro de téléphone dans votre profil : l'agent Kwa-Ba vous appellera pour la visite.")
    if identite_verifiee(hote):
        return
    en_attente = HebergementModel.objects.filter(host=hote).exclude(statut_verification='verifiee').count()
    if en_attente >= MAX_ANNONCES_HOTE_NON_VERIFIE:
        raise VerificationErreur(
            f"Vous avez déjà {en_attente} annonces en attente. Attendez la vérification de votre identité "
            "avant d'en ajouter d'autres.")


def visite_a_planifier(hebergement, modification: bool = False) -> None:
    """Tells the agents that a listing waits for a visit (new, or changed after verification).

    Only if the host's identity is verified and their agreement signed: otherwise, their listings will be sent to
    them at that moment (decider_piece, contrat_hote_signe)."""
    hote = hebergement.host
    if not identite_verifiee(hote) or contrat_manquant(hote):
        return
    _envoyer('visite_a_planifier', f"[Kwa-Ba] Visite à planifier : {hebergement.name} ({hebergement.city})",
             _verificateurs(), {
                 'modification': modification, 'hebergement': hebergement.name, 'ville': hebergement.city,
                 'adresse': hebergement.location, 'hote': f"{hote.first_name} {hote.last_name}".strip(),
                 'telephone': hote.phone or '-', 'email': hote.email,
                 'url': f"{settings.FRONTEND_URL}/agent",
             })


def contrat_hote_signe(hote) -> None:
    """The host has just signed their agreement: their pending listings are offered to the agents."""
    from apps.hebergements.models import HebergementModel

    for annonce in HebergementModel.objects.filter(host=hote, statut_verification='en_attente').select_related('host'):
        visite_a_planifier(annonce)


def piece_a_controler(piece) -> None:
    """Tells the agents that an identity document has just been sent (or replaced)."""
    hote = piece.hote
    _envoyer('piece_a_controler', f"[Kwa-Ba] Pièce d'identité à contrôler : {hote.first_name} {hote.last_name}".strip(),
             _verificateurs(), {
                 'hote': f"{hote.first_name} {hote.last_name}".strip(), 'email': hote.email,
                 'telephone': hote.phone or '-', 'type_piece': piece.get_type_piece_display(),
                 'url': f"{settings.FRONTEND_URL}/agent",
             })


@transaction.atomic
def decider_piece(hote, verificateur, *, decision: str, motif: str = '') -> PieceIdentiteModel:
    """Remote check of the identity document. Verified: the document is deleted (only the result is kept)
    and the host's pending listings are sent to the agents for a visit."""
    from apps.hebergements.models import HebergementModel

    piece = PieceIdentiteModel.objects.select_for_update().select_related('hote').filter(hote=hote).first()
    if not piece or piece.statut != 'soumise':
        raise VerificationErreur("Aucune pièce d'identité à contrôler pour cet hôte.")
    motif = motif.strip()
    contexte = {'prenom': hote.first_name, 'url_espace': f"{settings.FRONTEND_URL}/hote/espace"}

    if decision == 'verifiee':
        piece.statut, piece.verifiee_le, piece.verifiee_par, piece.motif_refus = (
            'verifiee', timezone.now(), verificateur, '')
        if piece.fichier:
            piece.fichier.delete(save=False)
        piece.save()
        annonces = list(HebergementModel.objects.filter(host=hote, statut_verification='en_attente').select_related('host'))
        for annonce in annonces:
            visite_a_planifier(annonce)
        _envoyer('identite_verifiee', "Votre identité est vérifiée", [hote.email],
                 {**contexte, 'nb_annonces': len(annonces), 'contrat_a_signer': contrat_manquant(hote)})
    elif decision == 'refusee':
        if len(motif) < 10:
            raise VerificationErreur("Expliquez le motif du refus à l'hôte (10 caractères au moins).")
        piece.statut, piece.motif_refus = 'refusee', motif
        if piece.fichier:
            piece.fichier.delete(save=False)
        piece.save()
        _envoyer('identite_refusee', "Votre pièce d'identité n'a pas pu être vérifiée", [hote.email],
                 {**contexte, 'motif': motif})
    else:
        raise VerificationErreur("Décision inconnue.")
    return piece


def remettre_en_verification(hebergement, avant: dict) -> bool:
    """After a change by the host: a refused listing goes back into verification, and a verified listing too
    if what the agent checked (address, city, photos) changed. Returns True if it is put back."""
    if hebergement.statut_verification == 'en_attente':
        return False
    change = any(avant[champ] != getattr(hebergement, champ) for champ in hebergement.CHAMPS_VERIFIES)
    if hebergement.statut_verification == 'verifiee' and not change:
        return False
    deja_verifiee = hebergement.statut_verification == 'verifiee'
    hebergement.statut_verification, hebergement.motif_refus = 'en_attente', ''
    hebergement.save(update_fields=['statut_verification', 'motif_refus', 'updated_at'])
    visite_a_planifier(hebergement, modification=deja_verifiee)
    return True


@transaction.atomic
def decider(hebergement, agent, *, decision: str, controles: dict, commentaire: str, photos: list) -> VisiteModel:
    """Saves the visit and publishes (or refuses) the listing. Validating requires every check to be ticked."""
    from apps.hebergements.models import HebergementModel  # local import: hebergements does not import this app

    hebergement = HebergementModel.objects.select_for_update().select_related('host').get(pk=hebergement.pk)
    if hebergement.statut_verification != 'en_attente':
        raise VerificationErreur("Cette annonce n'attend pas de visite.")
    controles = {cle: bool(controles.get(cle)) for cle in VisiteModel.CONTROLES}
    commentaire = commentaire.strip()
    if len(photos) > MAX_PHOTOS_VISITE:
        raise VerificationErreur(f"{MAX_PHOTOS_VISITE} photos au plus.")

    hote = hebergement.host
    piece = PieceIdentiteModel.objects.select_for_update().filter(hote=hote).first()
    if decision == 'validee':
        if not all(controles.values()):
            raise VerificationErreur("Pour valider, tous les points de contrôle doivent être vérifiés.")
        if not piece or piece.statut != 'verifiee':
            raise VerificationErreur("L'identité de l'hôte doit être vérifiée avant de valider son logement.")
        if contrat_manquant(hote):
            raise VerificationErreur("L'hôte doit d'abord signer son contrat (depuis son espace hôte).")
    elif decision == 'refusee':
        if len(commentaire) < 10:
            raise VerificationErreur("Expliquez le motif du refus à l'hôte (10 caractères au moins).")
    else:
        raise VerificationErreur("Décision inconnue.")

    contenus = [image_normalisee(photo) for photo in photos]  # before any write: an invalid photo stops everything
    visite = VisiteModel.objects.create(hebergement=hebergement, agent=agent, decision=decision,
                                        controles=controles, commentaire=commentaire)
    for contenu in contenus:
        photo = PhotoVisiteModel(visite=visite)
        photo.image.save('visite.jpg', contenu, save=False)
        photo.save()

    maintenant = timezone.now()
    if piece and decision == 'refusee' and not controles['identite']:
        # The person met does not match the document: the host will have to prove their identity again
        piece.statut, piece.motif_refus = 'refusee', commentaire
        piece.save(update_fields=['statut', 'motif_refus'])

    contexte = {'prenom': hote.first_name, 'hebergement': hebergement.name,
                'url_espace': f"{settings.FRONTEND_URL}/hote/espace",
                'url_annonce': f"{settings.FRONTEND_URL}/hebergements/{hebergement.id}"}
    if decision == 'validee':
        hebergement.statut_verification, hebergement.verifiee_le, hebergement.motif_refus = 'verifiee', maintenant, ''
        _envoyer('annonce_verifiee', f"Votre logement est vérifié : {hebergement.name}", [hote.email], contexte)
    else:
        hebergement.statut_verification, hebergement.motif_refus = 'refusee', commentaire
        _envoyer('annonce_refusee', f"Votre annonce n'est pas encore publiée : {hebergement.name}", [hote.email],
                 {**contexte, 'motif': commentaire})
    hebergement.save(update_fields=['statut_verification', 'verifiee_le', 'motif_refus', 'updated_at'])
    return visite
