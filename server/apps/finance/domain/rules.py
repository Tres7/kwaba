"""Rules of the ledger (FIN-01), pure: the application checks every line with them before writing, for a clear
message in French; the database checks again (migration 0003) and refuses whoever writes."""
from collections.abc import Iterable
from dataclasses import replace
from datetime import date, datetime, timezone

from .entities import (CAUTION, CAUTION_RETENUE, ENTREE, FONDS_DE_TIERS, SENS, SORTIE, Ecriture, Ecrivain, Ligne,
                       Mouvement, Referentiels)
from .exceptions import MouvementRefuse, RestitutionRefusee

# Codes of a line checked against their reference table: (field, table, optional, message if unknown, if inactive)
CODES = (
    ('offre', 'offres', False, 'Offre « {code} » inconnue : écriture refusée.',
     "L'offre {code} n'est pas ouverte : écriture refusée."),
    ('compte_argent', 'comptes_argent', False, "Compte d'argent « {code} » inconnu : écriture refusée.",
     "Le compte d'argent {code} est inactif : écriture refusée."),
    ('tiers_type', 'tiers_types', True, 'Type de tiers « {code} » inconnu : écriture refusée.',
     'Le type de tiers {code} est inactif : écriture refusée.'),
    ('moyen_paiement', 'moyens_paiement', True, 'Moyen de paiement « {code} » inconnu : écriture refusée.',
     'Le moyen de paiement {code} est inactif : écriture refusée.'),
)


def mois_de(moment: datetime) -> date:
    """Accounting month of an event: its first day, in UTC like the database session (Lomé is UTC+0)."""
    return moment.astimezone(timezone.utc).date().replace(day=1)


def premier_du_mois(mois: date) -> date:
    if mois.day != 1:
        raise RestitutionRefusee('Un mois comptable se désigne par son premier jour.')
    return mois


def texte(valeur: str | None) -> str | None:
    """Optional text of a line: blank is stored as NULL, like in the schema (the views test IS NULL)."""
    return (valeur or '').strip() or None


def preparer(ligne: Ligne, ref: Referentiels, *, origine: str, par_id=None, maintenant: datetime) -> Ecriture:
    """Checks one line against the rules of FIN-01 and gives what is to be written."""
    if type(ligne.montant) is not int or ligne.montant <= 0:
        raise MouvementRefuse('Le montant doit être un nombre entier de francs CFA, strictement positif '
                              '(le sens porte le signe).')
    if ligne.sens not in SENS:
        raise MouvementRefuse(f'Sens « {ligne.sens} » inconnu : entree ou sortie.')
    nature = ref.natures.get(ligne.nature)
    if nature is None:
        raise MouvementRefuse(f'Nature « {ligne.nature} » inconnue : écriture refusée.')
    if not nature.actif:
        raise MouvementRefuse(f'Nature {nature.code} inactive : écriture refusée.')
    if nature.sens_attendu and nature.sens_attendu != ligne.sens:
        raise MouvementRefuse(f'La nature {nature.code} attend le sens {nature.sens_attendu}, reçu {ligne.sens}.')
    for champ, table, facultatif, inconnu, inactif in CODES:
        code = getattr(ligne, champ)
        if code is None and facultatif:
            continue
        actifs = getattr(ref, table)
        if code not in actifs:
            raise MouvementRefuse(inconnu.format(code=code))
        if not actifs[code]:
            raise MouvementRefuse(inactif.format(code=code))
    if ligne.tiers_id is not None and ligne.tiers_type is None:
        raise MouvementRefuse("Un identifiant de tiers va avec son type (hote, chauffeur…).")
    # Partner money is owed to a kind of partner; the person may still be to designate (the driver of a transfer is
    # assigned after the payment), then the line is moved to them
    if nature.famille == FONDS_DE_TIERS and ligne.tiers_type is None:
        raise MouvementRefuse(f'La nature {nature.code} (fonds de tiers) exige le tiers à qui la somme est due.')
    if nature.famille == CAUTION and not (ligne.reservation_id or ligne.location_id):
        raise MouvementRefuse(f'La nature {nature.code} (caution) exige la réservation ou la location concernée.')
    motif = texte(ligne.motif)
    if nature.code == CAUTION_RETENUE and not motif:
        raise MouvementRefuse('C03 (caution retenue) exige un motif et la référence de la décision.')
    moment = ligne.date_evenement or maintenant
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise MouvementRefuse("La date de l'événement doit porter son fuseau horaire.")
    propre = replace(ligne, piece_reference=texte(ligne.piece_reference), externe_reference=texte(ligne.externe_reference),
                     prestation_type=texte(ligne.prestation_type), motif=motif, metadonnees=ligne.metadonnees or {},
                     date_evenement=moment)
    return Ecriture(ligne=propre, date_evenement=moment, mois=mois_de(moment), origine=origine, par_id=par_id)


def inverse(mouvement: Mouvement, *, motif: str | None, origine: str, par_id=None, maintenant: datetime) -> Ecriture:
    """The inverse line of a written line (FIN-01.3): same nature, offer, third party, account and amount, the other
    direction, today's date, and the reason. A correction does not get corrected: write a new line instead."""
    motif = texte(motif)
    if not motif:
        raise MouvementRefuse('Une correction exige un motif.')
    if mouvement.annule_mouvement_id:
        raise MouvementRefuse(f'La ligne {mouvement.id} est elle-même une correction : passez une nouvelle ligne.')
    ligne = replace(mouvement.ligne, sens=SORTIE if mouvement.ligne.sens == ENTREE else ENTREE, motif=motif,
                    date_evenement=maintenant)
    return Ecriture(ligne=ligne, date_evenement=maintenant, mois=mois_de(maintenant), origine=origine, par_id=par_id,
                    annule_mouvement_id=mouvement.id)


def ecarts_des_modules_ouverts(ecrivains: Iterable[Ecrivain], offres_actives: set[str], natures_actives: set[str]) -> list[str]:
    """Open modules that would write to an offer or a nature that is not active: their movements would be refused,
    and the action with them (a payment, a payout)."""
    ecarts = []
    for ecrivain in sorted(ecrivains, key=lambda e: e.nom):
        if not ecrivain.ouvert():
            continue
        offres = sorted(set(ecrivain.offres) - offres_actives)
        natures = sorted(set(ecrivain.natures) - natures_actives)
        if offres or natures:
            manque = ', '.join([*(f'offre {o}' for o in offres), *(f'nature {n}' for n in natures)])
            ecarts.append(f'Le module {ecrivain.nom} est ouvert mais écrirait dans : {manque} (inactive ou inconnue).')
    return ecarts
