"""Documents of a car rental: voucher, payment receipt and invoice lines (registered in documents)."""
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.documents.api import Document, Produit, date, fcfa, nom as _nom
from apps.paiements import api as paiements

from .models import LocationModel


def lignes_facture(loc) -> list[dict]:
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


def bon(loc) -> bytes:
    fuseau = ZoneInfo(loc.lieu_prise.fuseau)
    debut, fin = timezone.localtime(loc.debut, fuseau), timezone.localtime(loc.fin, fuseau)
    doc = Document('Bon de location', loc.reference, sous_titre=f"émis le {date(timezone.now())}",
                   destinataire=[_nom(loc.voyageur), loc.voyageur.email])
    lignes = [
        ('Véhicule', f"{loc.libelle} · {loc.get_formule_display()}"),
        ('Prise', f"{date(debut, 'l j F Y')} à {debut:%H:%M}, {loc.lieu_prise.nom}" + (f", {loc.adresse_prise}" if loc.adresse_prise else '')),
        ('Retour', f"{date(fin, 'l j F Y')} à {fin:%H:%M}, {loc.lieu_retour.nom}" + (f", {loc.adresse_retour}" if loc.adresse_retour else '')),
        ('Passagers', str(loc.passagers)), ('Conducteur', loc.conducteur),
        ('Caution', (fcfa(loc.caution) + (', payée en ligne et gardée par Kwa-Ba, remboursée après le retour du véhicule'
                                           if loc.caution_gardee else ', à régler au propriétaire à la remise du véhicule'))
         if loc.caution else ''),
        ('Déplacements', f"{loc.jours_hors_lome} jour(s) hors de Lomé, {loc.jours_hors_pays} jour(s) hors du pays"
         if loc.jours_hors_lome or loc.jours_hors_pays else ''),
    ]
    # The voucher is downloaded on the site: it never gives the owner nor the driver (contact details sent by email)
    if loc.statut in ('partenaire_assigne', 'terminee') and (loc.vehicule or loc.immatriculation):
        lignes.append(('Véhicule remis', ' · '.join(x for x in (loc.vehicule, loc.immatriculation) if x)))
    doc.bloc('Votre location', lignes)
    montants = [(ligne['libelle'], str(ligne['quantite']), fcfa(ligne['prix_unitaire']), fcfa(ligne['quantite'] * ligne['prix_unitaire']))
                for ligne in lignes_facture(loc)]
    if loc.caution_gardee:
        montants.append(('Caution (remboursée après le retour)', '1', fcfa(loc.caution_gardee), fcfa(loc.caution_gardee)))
    doc.montants(montants, [('Total payé', fcfa(loc.montant_a_payer))])
    return doc.en_pdf()


PRODUIT = Produit(
    type='location',
    charger=lambda pk: LocationModel.objects.filter(pk=pk).first(),
    proprietaire_id=lambda loc: loc.voyageur_id,
    reference=lambda loc: loc.reference,
    paye=lambda loc: paiements.paiement_reussi('location', loc.pk),
    recu=lambda loc: paiements.recu_pdf('location', loc.pk),
    bon=bon,
    facture=lambda loc: {'client_nom': _nom(loc.voyageur), 'client_email': loc.voyageur.email, 'lignes': lignes_facture(loc)},
)
