"""Documents of a stay: voucher, payment receipt and invoice lines (registered in documents at start-up)."""
from django.utils import timezone

from apps.documents.api import Document, Produit, date, fcfa, nom as _nom
from apps.paiements import api as paiements

from .models import ReservationModel


def _heure(t) -> str:
    return t.strftime('%H h %M').replace(' 00', '') if t else ''


def bon(r) -> bytes:
    h = r.hebergement
    doc = Document('Bon de réservation', r.reference, sous_titre=f"émis le {date(timezone.now())}",
                   destinataire=[_nom(r.guest), r.guest.email])
    doc.bloc('Votre séjour', [
        ('Logement', h.name), ('Adresse', ', '.join(x for x in (h.location, h.city) if x)),
        ('Arrivée', f"{date(r.check_in, 'l j F Y')}" + (f", à partir de {_heure(h.arrivee_a_partir)}" if h.arrivee_a_partir else '')),
        ('Départ', f"{date(r.check_out, 'l j F Y')}" + (f", avant {_heure(h.depart_avant)}" if h.depart_avant else '')),
        ('Durée', f"{r.nights} nuit(s)"), ('Voyageurs', str(r.guests_count)),
        ('Hôte', _nom(h.host) + ', contact par la messagerie Kwa-Ba'),
    ])
    lignes = []
    if r.prix_nuits is not None:
        lignes.append((f"Hébergement, {r.nights} nuit(s)", str(r.nights), fcfa(r.prix_nuits // max(r.nights, 1)), fcfa(r.prix_nuits)))
        lignes.append(('Frais de service Kwa-Ba', '1', fcfa(r.frais_service or 0), fcfa(r.frais_service or 0)))
    else:
        lignes.append(('Séjour', '1', fcfa(r.total_price), fcfa(r.total_price)))
    doc.montants(lignes, [('Total payé', fcfa(r.total_price))])
    doc.bloc('Annulation', [('Conditions', paiements.texte_politique(r))])
    doc.paragraphe("Présentez ce bon (sur votre téléphone ou imprimé) à votre arrivée.", 'petit')
    return doc.en_pdf()


def lignes_facture(r) -> list[dict]:
    """Invoice lines of a paid stay (amounts including tax in FCFA)."""
    h = r.hebergement
    if r.prix_nuits is None:
        return [{'libelle': f"Séjour « {h.name} » du {date(r.check_in)} au {date(r.check_out)}",
                 'quantite': 1, 'prix_unitaire': int(r.total_price)}]
    lignes = [{'libelle': f"Hébergement « {h.name} », {h.city}, du {date(r.check_in)} au {date(r.check_out)}",
               'quantite': r.nights, 'prix_unitaire': r.prix_nuits // max(r.nights, 1)}]
    reste = r.prix_nuits - lignes[0]['quantite'] * lignes[0]['prix_unitaire']
    if reste:
        lignes.append({'libelle': 'Arrondi', 'quantite': 1, 'prix_unitaire': reste})
    lignes.append({'libelle': 'Frais de service Kwa-Ba', 'quantite': 1, 'prix_unitaire': r.frais_service or 0})
    return lignes


PRODUIT = Produit(
    type='reservation',
    charger=lambda pk: ReservationModel.objects.filter(pk=pk).first(),
    proprietaire_id=lambda r: r.guest_id,
    reference=lambda r: r.reference,
    paye=lambda r: paiements.paiement_reussi('reservation', r.pk),
    recu=lambda r: paiements.recu_pdf('reservation', r.pk),
    bon=bon,
    facture=lambda r: {'client_nom': _nom(r.guest), 'client_email': r.guest.email, 'lignes': lignes_facture(r)},
)
