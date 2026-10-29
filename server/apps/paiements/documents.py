"""Payment receipt (PDF), attached to the confirmation emails and downloaded by the payer."""
from apps.documents.api import Document, date, fcfa, nom as _nom

from .models import PaiementModel


def recu_paiement(p: PaiementModel) -> bytes:
    payeur = p.payeur
    doc = Document('Reçu de paiement', p.reference, sous_titre=f"paiement du {date(p.mis_a_jour_le)}",
                   destinataire=[_nom(payeur), payeur.email])
    moyen = ('PayPal' if p.prestataire == 'paypal' else 'Carte bancaire' if 'card' in (p.mode or '')
             else 'Mobile Money' if p.mode else 'FedaPay')
    doc.bloc('Paiement', [
        ('Objet', p.libelle), ('Référence', p.reference), ('Date', date(p.mis_a_jour_le, 'j F Y à H:i')),
        ('Moyen', moyen), ('Transaction', p.transaction_id or '-'),
        ('Montant en euros', f"{p.montant_eur} €".replace('.', ',') if p.montant_eur else ''),
    ])
    doc.montants([('Montant payé', '1', fcfa(p.montant), fcfa(p.montant))], [('Total', fcfa(p.montant))])
    doc.paragraphe("Ce reçu atteste le paiement. Il ne remplace pas une facture.", 'petit')
    return doc.en_pdf()
