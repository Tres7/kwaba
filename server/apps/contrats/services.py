"""Contracts: issuing (frozen text, variables replaced), personal signature link, signature and proofs.

Flow:
1. Kwa-Ba issues the contract (the back-office for a rental company, a driver or an NGO; automatically for a
   host, who signs it from their space). Kwa-Ba's legal representative is its signer.
2. The party receives a personal link (valid 30 days, stored hashed), reads the contract, types their name,
   draws their signature and expressly accepts.
3. The signed PDF (with signature certificate) is frozen, its SHA-256 fingerprint kept, and sent to
   both parties.
"""
import base64
import binascii
import hashlib
import logging
import re
import secrets
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from apps.documents.api import date, societe as _societe
from apps.give import api as give
from apps.locations import api as locations
from apps.paiements import api as paiements
from apps.transferts import api as transferts
from apps.notifications.api import send_mail

from .models import ContratModel, ModeleContratModel, hacher_jeton

logger = logging.getLogger('apps.contrats')

VALIDITE_LIEN = timedelta(days=30)
TAILLE_MAX_SIGNATURE = 400_000  # bytes, drawn image encoded in base64 included

DESIGNATIONS = {'hote': "l'Hôte", 'hotel': "l'Établissement", 'loueur': 'le Propriétaire', 'chauffeur': 'le Chauffeur',
                'ong': "l'Association"}
# Contracts signed by a host account: individual (B1) or hotel and serviced residence (B2)
TYPES_HOTE = ('hote', 'hotel')

# Variables usable in the templates (shown in the back-office editor)
VARIABLES = {
    'societe.raison_sociale': 'Raison sociale de Kwa-Ba', 'societe.forme_juridique': 'Forme juridique',
    'societe.adresse': 'Adresse du siège', 'societe.pays': 'Pays', 'societe.rccm': 'RCCM', 'societe.nif': 'NIF',
    'societe.site': 'Site web', 'societe.representant': 'Représentant légal et sa qualité',
    'partie.nom': 'Nom de la partie', 'partie.email': 'Email', 'partie.telephone': 'Téléphone',
    'partie.coordonnees': "« joignable au … et à l'adresse … »", 'partie.details': 'Précisions (véhicule, enregistrement…)', 'partie.designation': "« l'Hôte », « le Propriétaire »…",
    'partie.fondateur': "Programme Fondateurs : « applicable du … au … » ou « non applicable »",
    'date': "Date d'émission", 'tarifs.frais_voyageur': 'Frais de service voyageur (%)',
    'tarifs.commission_hote': 'Commission hôte (%)', 'tarifs.commission_chauffeur': 'Commission chauffeur (%)',
    'tarifs.commission_loueur': 'Commission loueur (%)', 'tarifs.delai_location': 'Délai minimal de réservation (jours)',
    'tarifs.restitution_caution': 'Délai de signalement des dommages après la location (heures)',
    'give.jour_reversement': 'Jour du reversement mensuel aux ONG',
}
_VARIABLE = re.compile(r'\{\{\s*([\w.]+)\s*\}\}')
FACULTATIVES = {'partie.details', 'partie.coordonnees'}


CHAMPS_PARTIE = {'hote': 'hote_id', 'hotel': 'hote_id', 'chauffeur': 'chauffeur_id', 'loueur': 'loueur_id',
                 'ong': 'organisation_id'}


class ContratErreur(Exception):
    """Message affichable."""


# --- Texte -----------------------------------------------------------------------------------------

def _pourcent(valeur) -> str:
    texte = f"{float(valeur):.2f}".rstrip('0').rstrip('.').replace('.', ',')
    return f"{texte} %"


def _tarifs() -> dict:
    location = locations.parametres_contrat()
    return {
        'tarifs.frais_voyageur': _pourcent(paiements.frais_voyageur() * 100),
        'tarifs.commission_hote': _pourcent(paiements.commission_hote() * 100),
        'tarifs.commission_chauffeur': _pourcent(transferts.commission_chauffeur() * 100),
        'tarifs.commission_loueur': _pourcent(location['commission_pourcent']) if location else '',
        'tarifs.delai_location': str(location['delai_min_jours']) if location else '2',
        'tarifs.restitution_caution': str(location['restitution_caution_heures']) if location else '24',
        'give.jour_reversement': str(give.jour_reversement()),
    }


def _nom(u) -> str:
    return f"{u.first_name} {u.last_name}".strip() or u.email


def partie(type_contrat: str, objet) -> dict:
    """Contact details of the party, copied into the contract, and the link to it.

    `objet`: the host account, or the party given by its module (transferts, locations or give public API)."""
    if type_contrat in TYPES_HOTE:
        return {'nom': _nom(objet), 'email': objet.email, 'telephone': objet.phone or '', 'details': '',
                'fondateur': fondateur(objet), 'lien': {'hote': objet}}
    return {'nom': objet['nom'], 'email': objet['email'], 'telephone': objet['telephone'], 'details': objet['details'],
            'lien': {CHAMPS_PARTIE[type_contrat]: objet['id']}}


def fondateur(objet) -> str:
    """The host's Founders Programme, as it appears in the contract (dates set by the team)."""
    c = paiements.conditions_hote(objet.pk)
    if c and c['categorie'] == 'particulier' and c['fondateur_debut'] and c['fondateur_fin']:
        return f"applicable du {date(c['fondateur_debut'])} au {date(c['fondateur_fin'])}"
    return 'non applicable'


def _coordonnees(telephone: str, email: str) -> str:
    """« joignable au … et à l'adresse … » (reachable at … and at the address …), without the missing part."""
    morceaux = [f"au {telephone}" if telephone else '', f"à l'adresse {email}" if email else '']
    return f"joignable {' et '.join(m for m in morceaux if m)}" if any(morceaux) else ''


def contexte(type_contrat: str, infos: dict) -> dict:
    s = _societe()
    representant = ', '.join(x for x in (s.representant_nom, s.representant_qualite) if x) or 'son représentant légal'
    return {
        'societe.raison_sociale': s.raison_sociale or s.nom_commercial, 'societe.forme_juridique': s.forme_juridique,
        'societe.adresse': s.adresse, 'societe.pays': s.pays, 'societe.rccm': s.rccm, 'societe.nif': s.nif,
        'societe.site': s.site, 'societe.representant': representant,
        'partie.nom': infos['nom'], 'partie.email': infos['email'], 'partie.telephone': infos['telephone'],
        'partie.coordonnees': _coordonnees(infos['telephone'], infos['email']),
        'partie.details': infos['details'], 'partie.designation': DESIGNATIONS[type_contrat],
        'partie.fondateur': infos.get('fondateur') or 'non applicable',
        'date': date(timezone.now()), **_tarifs(),
    }


def rendre(corps: str, valeurs: dict) -> str:
    """Replaces the variables; a missing value stays visible to be completed ("[à compléter]")."""
    def valeur(m):
        cle = m.group(1)
        return str(valeurs.get(cle) or ('' if cle in FACULTATIVES else '[à compléter]'))

    texte = _VARIABLE.sub(valeur, corps)
    # An empty detail leaves ", ," or a space before the comma: clean it up
    texte = re.sub(r' +([,.])', r'\1', re.sub(r',[ \t]*,', ',', texte))
    return re.sub(r'[ \t]{2,}', ' ', texte)


def blocs(corps: str) -> list[dict]:
    """Paragraphs of the contract: {'type': 'titre' | 'texte', 'texte': …}. "##" at the start = article title."""
    resultat = []
    for paragraphe in re.split(r'\n\s*\n', corps.strip()):
        paragraphe = paragraphe.strip()
        if not paragraphe:
            continue
        if paragraphe.startswith('## '):
            titre, _, reste = paragraphe[3:].partition('\n')
            resultat.append({'type': 'titre', 'texte': titre.strip()})
            if reste.strip():
                resultat.append({'type': 'texte', 'texte': reste.strip()})
        else:
            resultat.append({'type': 'texte', 'texte': paragraphe})
    return resultat


# --- Drawn signature ----------------------------------------------------------------------------

def signature_png(contenu: bytes, fond_blanc_transparent=False) -> bytes:
    """Signature image checked, cropped and re-encoded as PNG (no original data kept)."""
    try:
        with Image.open(BytesIO(contenu)) as sonde:
            if sonde.format not in ('PNG', 'JPEG', 'WEBP'):
                raise ContratErreur("Signature : format d'image non pris en charge.")
            if sonde.width * sonde.height > 4000 * 4000:
                raise ContratErreur("Signature : image trop grande.")
            sonde.verify()
        image = Image.open(BytesIO(contenu)).convert('RGBA')
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ContratErreur("Signature illisible.") from None
    if fond_blanc_transparent:
        # Scanned signature: the light background becomes transparent
        image.putdata([(r, g, b, 0) if r > 225 and g > 225 and b > 225 else (r, g, b, a) for r, g, b, a in image.getdata()])
    cadre = image.getchannel('A').point(lambda a: 255 if a > 20 else 0).getbbox()
    if not cadre or (cadre[2] - cadre[0]) < 30 or (cadre[3] - cadre[1]) < 10:
        raise ContratErreur("La signature est vide ou trop petite : dessinez-la dans le cadre.")
    image = image.crop(cadre)
    image.thumbnail((900, 300))
    tampon = BytesIO()
    image.save(tampon, 'PNG', optimize=True)
    return tampon.getvalue()


def _depuis_data_url(valeur: str) -> bytes:
    if not isinstance(valeur, str) or len(valeur) > TAILLE_MAX_SIGNATURE * 4 // 3 + 100:
        raise ContratErreur("Signature manquante ou trop lourde.")
    entete, _, donnees = valeur.partition(',')
    if not re.fullmatch(r'data:image/(png|jpeg|webp);base64', entete):
        raise ContratErreur("Signature manquante.")
    try:
        return base64.b64decode(donnees, validate=True)
    except (binascii.Error, ValueError):
        raise ContratErreur("Signature illisible.") from None


# --- Emails -----------------------------------------------------------------------------------------

def _envoyer(gabarit: str, sujet: str, destinataires: list[str], contexte_email: dict, pieces=None) -> None:
    def envoyer():
        try:
            send_mail(sujet, render_to_string(f'emails/contrats/{gabarit}.txt', contexte_email),
                      settings.DEFAULT_FROM_EMAIL, destinataires, pieces_jointes=pieces)
        except Exception:
            logger.exception("Email %s non envoyé", gabarit)

    destinataires = [d for d in destinataires if d]
    if destinataires:
        transaction.on_commit(envoyer)


def _destinataires_kwaba() -> list[str]:
    societe = _societe()
    if societe.email:
        return [societe.email]
    return list(get_user_model().objects.filter(role='admin', is_active=True).values_list('email', flat=True)[:5])


def lien(jeton: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/contrat/{jeton}"


def _envoyer_lien(contrat: ContratModel, jeton: str) -> None:
    _envoyer('a_signer', f"Votre contrat Kwa-Ba à signer : {contrat.reference}", [contrat.partie_email], {
        'nom': contrat.partie_nom, 'titre': contrat.titre, 'reference': contrat.reference, 'lien': lien(jeton),
        'expire_le': date(contrat.expire_le),
    })
    contrat.envoye_le = timezone.now()
    contrat.save(update_fields=['envoye_le'])


# --- Issuing ---------------------------------------------------------------------------------------

def _reference() -> str:
    return f"CT-{timezone.localdate().year}-{secrets.token_hex(3).upper()}"


@transaction.atomic
def emettre(type_contrat: str, objet, par=None, envoyer=True) -> ContratModel:
    """Contract prefilled for this party; sends the signature link by email if `envoyer`."""
    societe = _societe()
    if not societe.complets:
        raise ContratErreur("Renseignez la raison sociale et l'adresse de la société (Back-office → Documents) avant d'émettre un contrat.")
    modele = ModeleContratModel.objects.filter(type=type_contrat).first()
    if not modele:
        raise ContratErreur("Aucun modèle pour ce type de contrat.")
    infos = partie(type_contrat, objet)
    if envoyer and not infos['email']:
        raise ContratErreur("Cette partie n'a pas d'adresse email : ajoutez-la avant d'envoyer le contrat.")
    jeton = secrets.token_urlsafe(32)
    representant = ', '.join(x for x in (societe.representant_nom, societe.representant_qualite) if x)
    try:
        with transaction.atomic():
            contrat = ContratModel.objects.create(
                reference=_reference(), type=type_contrat, titre=modele.titre, version_modele=modele.version,
                corps=rendre(modele.corps, contexte(type_contrat, infos)),
                partie_nom=infos['nom'], partie_email=infos['email'] or '', partie_telephone=infos['telephone'] or '',
                cree_par=par, kwaba_signataire=f"{societe.raison_sociale}" + (f", représentée par {representant}" if representant else ''),
                jeton_hash=hacher_jeton(jeton), expire_le=timezone.now() + VALIDITE_LIEN, **infos['lien'],
            )
    except IntegrityError:
        raise ContratErreur("Un contrat est déjà en cours pour cette partie : renvoyez-le ou annulez-le d'abord.") from None
    if envoyer:
        _envoyer_lien(contrat, jeton)
    return contrat


def renvoyer(contrat: ContratModel) -> ContratModel:
    """New link (the old one no longer works), valid 30 days, sent by email."""
    if contrat.statut != 'a_signer':
        raise ContratErreur("Seul un contrat à signer peut être renvoyé.")
    if not contrat.partie_email:
        raise ContratErreur("Cette partie n'a pas d'adresse email.")
    jeton = secrets.token_urlsafe(32)
    contrat.jeton_hash, contrat.expire_le = hacher_jeton(jeton), timezone.now() + VALIDITE_LIEN
    contrat.save(update_fields=['jeton_hash', 'expire_le'])
    _envoyer_lien(contrat, jeton)
    return contrat


def annuler(contrat: ContratModel, motif: str) -> ContratModel:
    if contrat.statut == 'annule':
        raise ContratErreur("Ce contrat est déjà annulé.")
    if len(motif.strip()) < 5:
        raise ContratErreur("Indiquez le motif de l'annulation.")
    contrat.statut, contrat.annule_le, contrat.motif_annulation = 'annule', timezone.now(), motif.strip()
    contrat.save(update_fields=['statut', 'annule_le', 'motif_annulation'])
    return contrat


def par_jeton(jeton: str) -> ContratModel | None:
    if not jeton or len(jeton) > 100:
        return None
    return ContratModel.objects.filter(jeton_hash=hacher_jeton(jeton)).exclude(statut='annule').first()


# --- Hosts ------------------------------------------------------------------------------------------

def type_contrat_hote(hote) -> str:
    """Contract the host must sign: individual host (B1) or hotel and serviced residence (B2)."""
    c = paiements.conditions_hote(hote.pk)
    return 'hotel' if c and c['categorie'] == 'hotel' else 'hote'


def contrat_hote(hote) -> ContratModel:
    """The host's contract, issued on the first request (they sign it from their space, without email)."""
    contrat = ContratModel.objects.filter(hote=hote).exclude(statut='annule').first()
    return contrat or emettre(type_contrat_hote(hote), hote, envoyer=False)


def hote_a_signe(hote) -> bool:
    return ContratModel.objects.filter(hote=hote, statut='signe').exists()


def hotes_a_inviter():
    """Active hosts who pre-registered or created a listing and have not signed their agreement yet."""
    return (get_user_model().objects.filter(role='hote', is_active=True)
            .filter(Q(preinscriptions__isnull=False) | Q(hebergements__isnull=False))
            .exclude(contrats__statut='signe').distinct())


def inviter_hotes_a_signer() -> int:
    """The company has just been registered (RCCM and NIF): each host still to sign receives an email, in the language
    of their pre-registration, pointing to the agreement in their host space. Returns the number of emails sent."""
    site = settings.FRONTEND_URL.rstrip('/')
    envoyes = 0
    for hote in hotes_a_inviter():
        derniere = hote.preinscriptions.first()  # most recent first (Meta.ordering)
        langue = derniere.langue if derniere else 'fr'
        sujet = 'Your Kwa-Ba host agreement is ready to sign' if langue == 'en' else 'Votre contrat hôte Kwa-Ba est prêt à signer'
        corps = render_to_string('emails/contrats/contrat_disponible.txt', {
            'langue': langue, 'prenom': hote.first_name,
            'lien': f"{site}{'/en' if langue == 'en' else ''}/hote/espace/contrat",
        })
        try:
            envoyes += send_mail(sujet, corps, settings.DEFAULT_FROM_EMAIL, [hote.email])
        except Exception:
            logger.exception("Invitation à signer le contrat non envoyée (user_id=%s)", hote.pk)
    return envoyes


# --- Signature --------------------------------------------------------------------------------------

def signer(contrat: ContratModel, *, nom: str, signature: str, accepte: bool, ip: str | None, user_agent: str, methode: str) -> ContratModel:
    from .pdf import contrat_pdf

    with transaction.atomic():
        contrat = ContratModel.objects.select_for_update().get(pk=contrat.pk)
        if contrat.statut == 'signe':
            raise ContratErreur("Ce contrat est déjà signé.")
        if contrat.statut != 'a_signer':
            raise ContratErreur("Ce contrat n'est plus à signer.")
        if methode == 'lien personnel' and contrat.expire_le < timezone.now():
            raise ContratErreur("Ce lien a expiré : demandez à Kwa-Ba de vous renvoyer le contrat.")
        if not accepte:
            raise ContratErreur("Cochez la case pour accepter le contrat.")
        nom = ' '.join((nom or '').split())
        if len(nom) < 3 or len(nom) > 150:
            raise ContratErreur("Tapez votre nom complet.")
        image = signature_png(_depuis_data_url(signature))

        contrat.signataire_nom, contrat.signe_le, contrat.statut = nom, timezone.now(), 'signe'
        contrat.ip, contrat.user_agent, contrat.methode = ip, (user_agent or '')[:300], methode
        contrat.empreinte_texte = hashlib.sha256(contrat.corps.encode()).hexdigest()
        contrat.signature.save(f"{contrat.reference}.png", ContentFile(image), save=False)
        pdf = contrat_pdf(contrat)
        contrat.empreinte_pdf = hashlib.sha256(pdf).hexdigest()
        contrat.pdf.save(f"{contrat.reference}.pdf", ContentFile(pdf), save=False)
        contrat.save()

    if contrat.type in TYPES_HOTE and contrat.hote_id:
        from apps.verifications.api import contrat_hote_signe

        contrat_hote_signe(contrat.hote)
    piece = [(f"contrat-{contrat.reference}.pdf", pdf, 'application/pdf')]
    contexte_email = {'nom': contrat.partie_nom, 'titre': contrat.titre, 'reference': contrat.reference,
                      'signe_le': date(contrat.signe_le, 'j F Y à H:i'), 'empreinte': contrat.empreinte_pdf,
                      'type': contrat.get_type_display()}
    _envoyer('signe', f"Contrat signé : {contrat.reference}", [contrat.partie_email], contexte_email, piece)
    _envoyer('signe_kwaba', f"Contrat signé par {contrat.partie_nom} : {contrat.reference}", _destinataires_kwaba(), contexte_email, piece)
    return contrat
