"""Donation receipt (registered in documents at start-up)."""
from django.utils import timezone

from apps.documents.api import Document, Produit, date, fcfa, nom as _nom
from apps.paiements import api as paiements

from . import montants
from .models import DonModel


def recu(d) -> bytes:
    doc = Document('Reçu de don', d.reference, sous_titre=f"don du {date(d.paye_le)}", destinataire=[_nom(d.donateur), d.donateur.email])
    reversement = montants.date_reversement(timezone.localtime(d.paye_le).date())
    doc.bloc('Votre don', [
        ('Association', f"{d.organisation.nom}, {d.organisation.ville}"), ('Projet', d.projet.titre if d.projet_id else 'Don libre'),
        ("N° d'enregistrement", d.organisation.numero_enregistrement), ('Reversement prévu', f"au plus tard le {date(reversement)}"),
    ])
    lignes = [('Don', '1', fcfa(d.montant), fcfa(d.montant))]
    if d.couvre_frais and d.frais:
        lignes.append(('Frais de paiement (ajoutés par vous)', '1', fcfa(d.frais), fcfa(d.frais)))
    doc.montants(lignes, [('Reversé à l’association', fcfa(d.montant_ong)), ('Total payé', fcfa(d.total))])
    doc.paragraphe("Kwa-Ba ne prélève aucune commission sur les dons. La preuve du reversement est publiée sur la page de l'association.", 'petit')
    return doc.en_pdf()


PRODUIT = Produit(
    type='don',
    charger=lambda pk: DonModel.objects.filter(pk=pk).first(),
    proprietaire_id=lambda d: d.donateur_id,
    reference=lambda d: d.reference,
    paye=lambda d: paiements.paiement_reussi('don', d.pk),
    recu=recu,
    prefixe_recu='recu-don',
)
