"""Content of the invoices. Vouchers and receipts are built by the module of each product (documents.api)."""
from .models import FactureModel
from .pdf import Document, date, fcfa


def nom(u) -> str:
    return f"{u.first_name} {u.last_name}".strip() or u.email


def facture(f: FactureModel) -> bytes:
    doc = Document('Facture', f.numero, sous_titre=f"émise le {date(f.emise_le)}",
                   destinataire=[x for x in (f.client_nom, f.client_adresse, f.client_email) if x])
    lignes = [(lg['libelle'], str(lg['quantite']), fcfa(lg['prix_unitaire']), fcfa(lg['quantite'] * lg['prix_unitaire'])) for lg in f.lignes]
    totaux = [('Total', fcfa(f.total_ttc))]
    if f.tva:
        totaux = [('Total HT', fcfa(f.total_ht)), (f"TVA {str(f.taux_tva).rstrip('0').rstrip('.').replace('.', ',')} %", fcfa(f.tva)),
                  ('Total TTC', fcfa(f.total_ttc))]
    doc.montants(lignes, totaux)
    if not f.tva:
        doc.paragraphe('TVA non applicable.', 'petit')
    if f.objet_type != 'libre':
        doc.paragraphe('Facture acquittée : réglée en ligne lors de la réservation.', 'petit')
    return doc.en_pdf()
