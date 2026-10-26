"""Content of the documents: vouchers (stay, transfer, rental), receipts (payment, donation) and invoices."""
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.give import montants as montants_dons
from apps.paiements import tarifs
from apps.paiements.models import PaiementModel

from .models import FactureModel
from .pdf import Document, date, fcfa


def _nom(u) -> str:
    return f"{u.first_name} {u.last_name}".strip() or u.email


def paiement_reussi(objet) -> PaiementModel | None:
    champ = {'ReservationModel': 'reservation', 'TransfertModel': 'transfert', 'LocationModel': 'location',
             'DonModel': 'don'}[type(objet).__name__]
    return PaiementModel.objects.filter(**{champ: objet}, statut='reussi').order_by('cree_le').first()


def _heure(t) -> str:
    return t.strftime('%H h %M').replace(' 00', '') if t else ''


# --- Bons -----------------------------------------------------------------------------------------

def bon_reservation(r) -> bytes:
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
    doc.bloc('Annulation', [('Conditions', tarifs.texte_politique(r))])
    doc.paragraphe("Présentez ce bon (sur votre téléphone ou imprimé) à votre arrivée.", 'petit')
    return doc.en_pdf()


def bon_transfert(t) -> bytes:
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


def bon_location(loc) -> bytes:
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
    from .services import lignes_de

    montants = [(ligne['libelle'], str(ligne['quantite']), fcfa(ligne['prix_unitaire']), fcfa(ligne['quantite'] * ligne['prix_unitaire']))
                for ligne in lignes_de(loc)]
    if loc.caution_gardee:
        montants.append(('Caution (remboursée après le retour)', '1', fcfa(loc.caution_gardee), fcfa(loc.caution_gardee)))
    doc.montants(montants, [('Total payé', fcfa(loc.montant_a_payer))])
    return doc.en_pdf()


# --- Receipts ----------------------------------------------------------------------------------------

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


def recu_don(d) -> bytes:
    doc = Document('Reçu de don', d.reference, sous_titre=f"don du {date(d.paye_le)}", destinataire=[_nom(d.donateur), d.donateur.email])
    reversement = montants_dons.date_reversement(timezone.localtime(d.paye_le).date())
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


# --- Factures -------------------------------------------------------------------------------------

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
