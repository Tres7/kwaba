"""Rental emails, sent by the worker (same principle as apps.transferts.notifications)."""
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import formats, timezone

from apps.paiements import api as paiements
from apps.securite import coordonnees
from apps.transferts import api as transferts

from .models import LocationModel, ParametresLocationModel, VersementChauffeurLocationModel, VersementPartenaireModel

logger = logging.getLogger('apps.locations.notifications')

ALERTE_SANS_PARTENAIRE = timedelta(hours=48)


def _date(location: LocationModel, moment) -> str:
    return formats.date_format(moment.astimezone(ZoneInfo(location.lieu_prise.fuseau)), 'l j F Y à H\\hi')


def _restitution_heures() -> int:
    params = ParametresLocationModel.courants()
    return params.restitution_caution_heures if params else 24


def _location(loc: LocationModel) -> dict:
    return {
        'reference': loc.reference, 'categorie': loc.libelle, 'exemple': loc.categorie.exemple_modele if loc.categorie_id else '',
        'formule': loc.get_formule_display(), 'avec_chauffeur': loc.avec_chauffeur,
        'chauffeur_seul': loc.formule == 'chauffeur_seul', 'formule_sans_chauffeur': loc.formule == 'sans_chauffeur',
        'prise': f"{loc.lieu_prise.nom}{', ' + loc.adresse_prise if loc.adresse_prise else ''}",
        'retour': f"{loc.lieu_retour.nom}{', ' + loc.adresse_retour if loc.adresse_retour else ''}",
        'debut': _date(loc, loc.debut), 'fin': _date(loc, loc.fin), 'jours': loc.jours, 'passagers': loc.passagers,
        'jours_hors_lome': loc.jours_hors_lome, 'jours_hors_pays': loc.jours_hors_pays,
        'primes': paiements.fcfa(loc.primes) if loc.primes else '',
        'precisions': loc.precisions, 'voyageur': f"{loc.voyageur.first_name} {loc.voyageur.last_name}".strip(),
        'telephone_voyageur': loc.telephone, 'conducteur': loc.conducteur, 'permis': loc.permis_numero,
        'permis_pays': loc.permis_pays, 'caution': paiements.fcfa(loc.caution) if loc.caution else '',
        'caution_en_ligne': bool(loc.caution_gardee), 'restitution_heures': _restitution_heures(),
        'chauffeur': loc.chauffeur_nom, 'telephone_chauffeur': loc.chauffeur_telephone,
        'vehicule': loc.vehicule, 'immatriculation': loc.immatriculation,
        'url': f"{settings.FRONTEND_URL}/location/{loc.id}",
    }


def confirmee(loc: LocationModel):
    paiements.envoyer_email('emails/locations/location_confirmee.txt', f"Réservation confirmée : {loc.lieu_prise.ville}", [loc.voyageur.email], {
        **_location(loc), 'prenom': loc.voyageur.first_name, 'montant': paiements.fcfa(loc.montant_a_payer),
    }, pieces_jointes=paiements.documents_joints(loc))


def a_attribuer(loc: LocationModel, urgent: bool = False):
    destinataires = paiements.emails_admins()
    if not destinataires:
        logger.error("Location %s à attribuer mais aucun administrateur à prévenir", loc.reference)
        return
    from .services import partenaires_disponibles

    demande = transferts.fiche_chauffeur(loc.chauffeur_demande_id) if loc.chauffeur_demande_id else None
    sujet = f"[Kwa-Ba] {'URGENT : ' if urgent else ''}Location à attribuer : {loc.reference}"
    paiements.envoyer_email('emails/locations/a_attribuer.txt', sujet, destinataires, {
        **_location(loc), 'urgent': urgent, 'nb_partenaires': partenaires_disponibles(loc).count(),
        'chauffeur_demande': f"{demande['prenom']} {demande['nom']}" if demande else '',
        'url_admin': f"{settings.BACKEND_URL}/admin/locations/locationmodel/{loc.id}/change/",
    })


def partenaire_au_voyageur(loc: LocationModel):
    p = loc.partenaire
    paiements.envoyer_email('emails/locations/partenaire_assigne.txt', f"Votre {'chauffeur' if loc.formule == 'chauffeur_seul' else 'véhicule'} à {loc.lieu_prise.ville}",
             [loc.voyageur.email], {
                 **_location(loc), 'prenom': loc.voyageur.first_name, 'partenaire': p.nom if p else '',
                 'contact': p.contact if p else '', 'telephone_partenaire': p.telephone if p else '',
                 'assistance': settings.ASSISTANCE_CONTACT,
             })


def _sans_telephone_du_voyageur(loc: LocationModel) -> dict:
    """Partners do not receive the traveller's phone number (nor those slipped into their details or address):
    to reach them, they go through Kwa-Ba."""
    infos = _location(loc)
    del infos['telephone_voyageur']
    return {**infos, **{cle: coordonnees.analyser(infos[cle])[0] for cle in ('prise', 'retour', 'precisions')}}


def location_au_partenaire(loc: LocationModel):
    p = loc.partenaire
    if not p or not p.email:
        return  # owner told by phone by the team
    paiements.envoyer_email('emails/locations/location_partenaire.txt', f"Nouvelle location Kwa-Ba : {_date(loc, loc.debut)}", [p.email], {
        **_sans_telephone_du_voyageur(loc), 'contact': p.contact,
        'montant': paiements.fcfa(loc.montant_partenaire), 'assistance': settings.ASSISTANCE_CONTACT,
    })


def mission_au_chauffeur(loc: LocationModel):
    c = transferts.fiche_chauffeur(loc.chauffeur_partenaire_id) if loc.chauffeur_partenaire_id else None
    if not c or not c['email']:
        return  # driver told by phone by the team
    paiements.envoyer_email('emails/locations/mission_chauffeur.txt', f"Mission Kwa-Ba : {_date(loc, loc.debut)}", [c['email']], {
        **_sans_telephone_du_voyageur(loc), 'prenom_chauffeur': c['prenom'],
        'montant': paiements.fcfa(loc.montant_chauffeur), 'assistance': settings.ASSISTANCE_CONTACT,
    })


def versement_au_partenaire(v: VersementPartenaireModel):
    p, loc = v.partenaire, v.location
    if not p.email:
        return
    paiements.envoyer_email('emails/locations/versement_partenaire.txt', f"Versement de {paiements.fcfa(v.montant)} envoyé", [p.email], {
        'contact': p.contact, 'reference': loc.reference, 'debut': _date(loc, loc.debut), 'montant': paiements.fcfa(v.montant),
        'montant_brut': paiements.fcfa(v.montant_brut), 'commission': paiements.fcfa(v.commission),
        'retenue': paiements.fcfa(loc.caution_retenue) if loc.caution_retenue else '', 'motif': loc.caution_motif,
    })


def caution_au_voyageur(loc: LocationModel):
    """Deposit return: amount given back, withheld amount and its reason; Mobile Money number to give if needed."""
    rendu = loc.caution - loc.caution_retenue
    paiements.envoyer_email('emails/locations/caution_restituee.txt', f"Restitution de votre caution : {loc.reference}", [loc.voyageur.email], {
        'prenom': loc.voyageur.first_name, 'reference': loc.reference, 'caution': paiements.fcfa(loc.caution),
        'rendu': paiements.fcfa(rendu), 'retenue': paiements.fcfa(loc.caution_retenue) if loc.caution_retenue else '',
        'motif': loc.caution_motif, 'numero_requis': paiements.numero_remboursement_requis('location', loc.pk),
        'url': f"{settings.FRONTEND_URL}/location/{loc.id}", 'assistance': settings.ASSISTANCE_CONTACT,
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


def _nom_chauffeur(chauffeur_id) -> str:
    c = transferts.fiche_chauffeur(chauffeur_id)
    return f"{c['prenom']} {c['nom']}" if c else f"chauffeur {chauffeur_id}"


def envoyer_notifications() -> int:
    qs = LocationModel.objects.select_related('voyageur', 'categorie', 'lieu_prise', 'lieu_retour', 'partenaire')
    payees = qs.filter(statut__in=('confirmee', 'partenaire_assigne'))
    total = _traiter(payees.filter(confirmation_notifiee=False), confirmee, 'confirmation_notifiee')
    total += _traiter(payees.filter(admins_notifies=False), a_attribuer, 'admins_notifies')
    total += _traiter(
        qs.filter(statut='confirmee', alerte_sans_partenaire=False, debut__lte=timezone.now() + ALERTE_SANS_PARTENAIRE),
        lambda loc: a_attribuer(loc, urgent=True), 'alerte_sans_partenaire',
    )
    assignees = qs.filter(statut='partenaire_assigne')
    total += _traiter(assignees.filter(partenaire_notifie=False), partenaire_au_voyageur, 'partenaire_notifie')
    total += _traiter(assignees.filter(location_envoyee_partenaire=False), location_au_partenaire, 'location_envoyee_partenaire')
    total += _traiter(assignees.filter(mission_envoyee_chauffeur=False), mission_au_chauffeur, 'mission_envoyee_chauffeur')
    total += _traiter(
        qs.filter(statut__in=('partenaire_assigne', 'terminee'), caution_en_ligne=True, caution__gt=0,
                  caution_restituee_le__isnull=False, caution_notifiee=False),
        caution_au_voyageur, 'caution_notifiee',
    )

    versements = VersementPartenaireModel.objects.select_related('partenaire', 'location__lieu_prise')
    total += _traiter(versements.filter(statut='envoye', notifie=False), versement_au_partenaire, 'notifie')
    total += _traiter(
        versements.filter(statut='echoue', notifie=False),
        lambda v: paiements.alerte_admin(
            'Versement à un propriétaire', v, f"{v.partenaire} ({v.mode} {v.numero})",
            reference=v.location.reference, libelle=f"Location {v.location.lieu_prise.ville}", section='locations',
        ),
        'notifie',
    )
    chauffeurs = VersementChauffeurLocationModel.objects.select_related('location__lieu_prise')
    # Payout sent: nothing to tell the driver (they see it on their Mobile Money); failure: alert to the team
    total += _traiter(chauffeurs.filter(statut='envoye', notifie=False), lambda v: None, 'notifie')
    total += _traiter(
        chauffeurs.filter(statut='echoue', notifie=False),
        lambda v: paiements.alerte_admin(
            'Versement à un chauffeur (location)', v, f"{_nom_chauffeur(v.chauffeur_id)} ({v.mode} {v.numero})",
            reference=v.location.reference, libelle=f"Location {v.location.lieu_prise.ville}", section='locations',
        ),
        'notifie',
    )
    return total
