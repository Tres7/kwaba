"""Invoice issuing (continuous numbering) and attachments of the confirmation emails."""
import logging
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from . import generateurs
from .models import FactureModel, ParametresSocieteModel, SequenceFactureModel
from .registre import PRODUITS

logger = logging.getLogger('apps.documents')


class DocumentErreur(Exception):
    """Message affichable."""


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


def facture_de(type_objet: str, objet, par=None) -> FactureModel:
    """Invoice of a paid stay, transfer or rental: issued only once, then always the same."""
    produit = PRODUITS[type_objet]
    existante = FactureModel.objects.filter(objet_type=type_objet, objet_id=objet.pk).first()
    if existante:
        return existante
    if not produit.paye(objet):
        raise DocumentErreur("Une facture n'est émise qu'après le paiement.")
    return _emettre(objet_type=type_objet, objet_id=objet.pk, client_adresse='', par=par, **produit.facture(objet))


def facture_libre(*, client_nom, client_email, client_adresse, lignes, par) -> FactureModel:
    return _emettre(objet_type='libre', objet_id=None, client_nom=client_nom, client_email=client_email,
                    client_adresse=client_adresse, lignes=lignes, par=par)


def pieces_confirmation(type_objet: str, objet_id) -> list[tuple[str, bytes, str]]:
    """PDFs attached to the confirmation email after payment. A generation failure never prevents the email."""
    pieces = []
    try:
        produit = PRODUITS[type_objet]
        objet = produit.charger(objet_id)
        reference = produit.reference(objet)
        if produit.bon:
            pieces.append((f"bon-{reference}.pdf", produit.bon(objet), 'application/pdf'))
        if produit.paye(objet):
            pieces.append((f"{produit.prefixe_recu}-{reference}.pdf", produit.recu(objet), 'application/pdf'))
    except Exception:
        logger.exception("Documents non générés pour %s %s", type_objet, objet_id)
    return pieces
