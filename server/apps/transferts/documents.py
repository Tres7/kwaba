"""Documents of an airport transfer: voucher, payment receipt and invoice lines (registered in documents)."""
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.documents.api import Document, Produit, date, fcfa, nom as _nom
from apps.paiements import api as paiements

from .models import TransfertModel


def bon(t) -> bytes:
    arrivee = timezone.localtime(t.arrivee, ZoneInfo(t.aeroport.fuseau))
    doc = Document('Bon de transfert', t.reference, sous_titre=f"émis le {date(timezone.now())}",
                   destinataire=[_nom(t.voyageur), t.voyageur.email])
    lignes = [
        ('Aéroport', f"{t.aeroport.nom} ({t.aeroport.code}), {t.aeroport.ville}"),
        ('Arrivée prévue', f"{date(arrivee, 'l j F Y')} à {arrivee:%H:%M} (heure locale)"), ('Vol', t.numero_vol),
        ('Destination', t.destination), ('Véhicule', t.get_categorie_display()),
        ('Passagers · bagages', f"{t.passagers} · {t.bagages}"), ('Téléphone à l’arrivée', t.telephone),
    ]
    if t.chauffeur_id:
        c = t.chauffeur
        lignes += [('Chauffeur', f"{c.prenom} {c.nom} · {c.telephone}"), ('Véhicule du chauffeur', f"{c.vehicule} · {c.immatriculation}")]
    doc.bloc('Votre transfert', lignes)
    doc.montants([(f"Transfert aéroport{' (tarif de nuit)' if t.majoration_nuit else ''}", '1', fcfa(t.prix), fcfa(t.prix))],
                 [('Total payé', fcfa(t.prix))])
    doc.paragraphe("Votre chauffeur vous attend à la sortie avec une pancarte à votre nom. 60 minutes d'attente incluses.", 'petit')
    return doc.en_pdf()


def lignes_facture(t) -> list[dict]:
    return [{'libelle': f"Transfert aéroport {t.aeroport.ville}, {t.get_categorie_display()}{' (nuit)' if t.majoration_nuit else ''}, "
                        f"vol {t.numero_vol}", 'quantite': 1, 'prix_unitaire': t.prix}]


PRODUIT = Produit(
    type='transfert',
    charger=lambda pk: TransfertModel.objects.filter(pk=pk).first(),
    proprietaire_id=lambda t: t.voyageur_id,
    reference=lambda t: t.reference,
    paye=lambda t: paiements.paiement_reussi('transfert', t.pk),
    recu=lambda t: paiements.recu_pdf('transfert', t.pk),
    bon=bon,
    facture=lambda t: {'client_nom': _nom(t.voyageur), 'client_email': t.voyageur.email, 'lignes': lignes_facture(t)},
)
