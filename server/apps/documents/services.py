"""Invoice issuing (continuous numbering) and attachments of the confirmation emails."""
import logging
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from . import generateurs
from .models import FactureModel, ParametresSocieteModel, SequenceFactureModel

logger = logging.getLogger('apps.documents')

TYPES = {'ReservationModel': 'reservation', 'TransfertModel': 'transfert', 'LocationModel': 'location'}


class DocumentErreur(Exception):
    """Message affichable."""


def _client(objet):
    u = getattr(objet, 'guest', None) or objet.voyageur
    return {'client_nom': generateurs._nom(u), 'client_email': u.email}


def lignes_de(objet) -> list[dict]:
    """Invoice lines of a paid object (amounts including tax in FCFA)."""
    if type(objet).__name__ == 'ReservationModel':
        r, h = objet, objet.hebergement
        if r.prix_nuits is None:
            return [{'libelle': f"Séjour « {h.name} » du {generateurs.date(r.check_in)} au {generateurs.date(r.check_out)}",
                     'quantite': 1, 'prix_unitaire': int(r.total_price)}]
        lignes = [{'libelle': f"Hébergement « {h.name} », {h.city}, du {generateurs.date(r.check_in)} au {generateurs.date(r.check_out)}",
                   'quantite': r.nights, 'prix_unitaire': r.prix_nuits // max(r.nights, 1)}]
        reste = r.prix_nuits - lignes[0]['quantite'] * lignes[0]['prix_unitaire']
        if reste:
            lignes.append({'libelle': 'Arrondi', 'quantite': 1, 'prix_unitaire': reste})
        lignes.append({'libelle': 'Frais de service Kwa-Ba', 'quantite': 1, 'prix_unitaire': r.frais_service or 0})
        return lignes
    if type(objet).__name__ == 'TransfertModel':
        t = objet
        return [{'libelle': f"Transfert aéroport {t.aeroport.ville}, {t.get_categorie_display()}{' (nuit)' if t.majoration_nuit else ''}, "
                            f"vol {t.numero_vol}", 'quantite': 1, 'prix_unitaire': t.prix}]
    loc = objet
    lignes = []
    if loc.prix_jour:
        lignes.append({'libelle': f"Location {loc.libelle} ({loc.get_formule_display()}), {loc.lieu_prise.ville}",
                       'quantite': loc.jours, 'prix_unitaire': loc.prix_jour})
    if loc.prix_chauffeur:
        lignes.append({'libelle': f"Chauffeur, {loc.lieu_prise.ville}", 'quantite': loc.jours, 'prix_unitaire': loc.prix_chauffeur // loc.jours})
    if loc.primes:
        lignes.append({'libelle': 'Primes de déplacement du chauffeur', 'quantite': 1, 'prix_unitaire': loc.primes})
    reste = loc.prix - sum(ligne['quantite'] * ligne['prix_unitaire'] for ligne in lignes)
    if reste:
        lignes.append({'libelle': 'Frais de remise et de retour', 'quantite': 1, 'prix_unitaire': reste})
    return lignes


def _numero() -> str:
    """Next number, assigned under a lock: two simultaneous issues cannot get the same one."""
    annee = timezone.localdate().year
    SequenceFactureModel.objects.get_or_create(annee=annee)
    seq = SequenceFactureModel.objects.select_for_update().get(annee=annee)
    seq.dernier += 1
    seq.save(update_fields=['dernier'])
    return f"F-{annee}-{seq.dernier:05d}"


@transaction.atomic
def _emettre(*, objet_type, objet_id, client_nom, client_email, client_adresse, lignes, par) -> FactureModel:
    societe = ParametresSocieteModel.courants()
    if not societe.complets:
        raise DocumentErreur("Renseignez la raison sociale et l'adresse de la société (Back-office → Documents) avant d'émettre une facture.")
    ttc = sum(int(lg['quantite']) * int(lg['prix_unitaire']) for lg in lignes)
    taux = societe.taux_tva if societe.assujetti_tva else Decimal('0')
    # Prices paid including tax: the VAT is extracted from the total
    ht = int((Decimal(ttc) / (1 + taux / 100)).quantize(Decimal('1'))) if taux else ttc
    f = FactureModel.objects.create(
        numero=_numero(), emise_par=par, objet_type=objet_type, objet_id=objet_id, client_nom=client_nom,
        client_email=client_email, client_adresse=client_adresse, lignes=lignes, total_ht=ht, tva=ttc - ht,
        total_ttc=ttc, taux_tva=taux,
    )
    f.pdf.save(f"{f.numero}.pdf", ContentFile(generateurs.facture(f)), save=True)
    return f


def facture_de(objet, par=None) -> FactureModel:
    """Invoice of a paid stay, transfer or rental: issued only once, then always the same."""
    objet_type = TYPES[type(objet).__name__]
    existante = FactureModel.objects.filter(objet_type=objet_type, objet_id=objet.pk).first()
    if existante:
        return existante
    if not generateurs.paiement_reussi(objet):
        raise DocumentErreur("Une facture n'est émise qu'après le paiement.")
    return _emettre(objet_type=objet_type, objet_id=objet.pk, client_adresse='', lignes=lignes_de(objet), par=par, **_client(objet))


def facture_libre(*, client_nom, client_email, client_adresse, lignes, par) -> FactureModel:
    return _emettre(objet_type='libre', objet_id=None, client_nom=client_nom, client_email=client_email,
                    client_adresse=client_adresse, lignes=lignes, par=par)


def pieces_confirmation(objet) -> list[tuple[str, bytes, str]]:
    """PDFs attached to the confirmation email after payment. A generation failure never prevents the email."""
    pieces = []
    try:
        nom = type(objet).__name__
        if nom == 'DonModel':
            pieces.append((f"recu-don-{objet.reference}.pdf", generateurs.recu_don(objet), 'application/pdf'))
            return pieces
        bon = {'ReservationModel': generateurs.bon_reservation, 'TransfertModel': generateurs.bon_transfert,
               'LocationModel': generateurs.bon_location}[nom]
        pieces.append((f"bon-{objet.reference}.pdf", bon(objet), 'application/pdf'))
        paiement = generateurs.paiement_reussi(objet)
        if paiement:
            pieces.append((f"recu-{objet.reference}.pdf", generateurs.recu_paiement(paiement), 'application/pdf'))
    except Exception:
        logger.exception("Documents non générés pour %s", getattr(objet, 'pk', objet))
    return pieces
