"""Money of the payments in the ledger of the finance module (FIN-03), written in the same transaction as the action
that moves it (FIN-01.6). The products give the split of what they sell; this module adds the money account, the
payment method and the provider's reference.

A product is in the ledger once it declares `offre` in its ProduitPaye (registre.py): today the stays. Until then its
money is not written (transfers and rentals come next, Give waits for its natures).

Stays, line by line (documentation/modules/finance.md):
- payment: T01 nights and T02 cleaning owed to the host, R01 service fees;
- arrival of the traveller: the commission leaves T01 for R02 (individual) or R03 (hotel);
- cancellation: what is refunded leaves T01, T02 and R01; Kwa-Ba's share of the kept nights goes to R08;
- refund decided: T05, owed to the traveller; refund sent: T05 leaves; payout to the host sent: T09.
"""
import logging
from dataclasses import dataclass

from apps.finance import api as finance

from . import tarifs
from .registre import PRODUITS

logger = logging.getLogger('apps.paiements')

COMPTES = {'fedapay': 'FEDAPAY', 'paypal': 'PAYPAL'}
OBJETS = ('reservation_id', 'transfert_id', 'location_id')


@dataclass(frozen=True)
class Part:
    """One part of a product's split: what it is (nature), how much, and to whom."""
    nature: str
    montant: int
    tiers_type: str | None = None
    tiers_id: object = None
    sens: str = finance.ENTREE


def offre_de(type_objet: str, objet_id) -> str | None:
    """Offer of a paid object in the ledger; None if its product is not in the ledger yet."""
    produit = PRODUITS.get(type_objet)
    return produit.offre(objet_id) if produit and produit.offre else None


def moyen(paiement) -> str | None:
    """Payment method of the ledger: Moov Money, Mixx by Yas or card (None for another operator)."""
    if paiement.prestataire == 'paypal':
        return 'PAYPAL'
    mode = (paiement.mode or '').lower()
    if 'moov' in mode or 'flooz' in mode:
        return 'MOOV'
    if any(nom in mode for nom in ('togocel', 'mixx', 'yas', 'tmoney', 't-money')):
        return 'MIXX'
    if any(nom in mode for nom in ('card', 'carte', 'visa', 'master')) or paiement.description.get('moyen') == 'carte':
        return 'CARTE'
    return None


def _objet(paiement) -> dict:
    return {nom: getattr(paiement, nom) for nom in OBJETS if getattr(paiement, nom, None)}


def _payeur_id(paiement):
    return getattr(paiement, 'payeur_id', None) or getattr(paiement.payeur, 'pk', None)


def _ligne(paiement, offre: str, part: Part, *, externe_reference: str | None) -> finance.Ligne:
    return finance.Ligne(
        nature=part.nature, offre=offre, montant=part.montant, sens=part.sens,
        compte_argent=COMPTES.get(paiement.prestataire, paiement.prestataire.upper()),
        tiers_type=part.tiers_type, tiers_id=part.tiers_id, moyen_paiement=moyen(paiement),
        piece_reference=paiement.reference, externe_reference=externe_reference, **_objet(paiement))


def ecrire(paiement, offre: str, parts: list[Part], *, origine: str, cle: str) -> list[int]:
    """Writes parts of the money of a payment, on the payment's money account. `cle`: reference of the event (the
    provider's id, or « arrivee:<id> » for an internal event), so that it is written once."""
    lignes = [_ligne(paiement, offre, part, externe_reference=cle) for part in parts if part.montant]
    return finance.enregistrer(lignes, origine=origine) if lignes else []


def encaisser(paiement, parts: list[Part]) -> None:
    """A payment received and accepted: its split, under the provider's reference of the transaction."""
    offre = offre_de(paiement.type_objet, paiement.objet_id)
    if offre is None:
        return
    total = sum(part.montant for part in parts)
    if total != paiement.montant:
        # I1/I2: what was collected must be classified to the franc
        raise finance.MouvementRefuse(f'Ventilation de {paiement.reference} incomplète : elle ne couvre pas le '
                                      'montant payé.')
    ecrire(paiement, offre, parts, origine='paiement', cle=paiement.transaction_id or f'paiement:{paiement.pk}')


def dans_le_grand_livre(type_objet: str, objet_id) -> bool:
    """The money of this object is in the ledger: its product writes there, and its payment was written (money paid
    before the ledger existed is never written afterwards, so that no line leaves what never came in)."""
    return offre_de(type_objet, objet_id) is not None and finance.a_des_lignes(**{f'{type_objet}_id': objet_id})


def du_au_voyageur(remboursement) -> None:
    """A refund decided: the money becomes owed to the traveller (T05). The caller has first taken it out of what
    it was (nights, cleaning, fees), except for a payment refused at once (`nouvel_encaissement`, set by the payment
    flow), whose money was never classified."""
    paiement = remboursement.paiement
    offre = offre_de(paiement.type_objet, paiement.objet_id)
    if offre is None:
        return
    if not (getattr(paiement, 'nouvel_encaissement', False) or dans_le_grand_livre(paiement.type_objet,
                                                                                    paiement.objet_id)):
        return
    ecrire(paiement, offre, [Part('T05', remboursement.montant, 'voyageur', _payeur_id(paiement))],
           origine='remboursement', cle=f'remboursement:{remboursement.pk}')


def remboursement_envoye(remboursement) -> None:
    """The refund left: T05 leaves the money account."""
    paiement = remboursement.paiement
    offre = offre_de(paiement.type_objet, paiement.objet_id)
    if offre is None or not finance.a_des_lignes(externe_reference=f'remboursement:{remboursement.pk}'):
        return
    ecrire(paiement, offre, [Part('T05', remboursement.montant, 'voyageur', _payeur_id(paiement), finance.SORTIE)],
           origine='remboursement', cle=remboursement.payout_id or f'remboursement-envoye:{remboursement.pk}')


# --- Stays -------------------------------------------------------------------------------------------------------

def _hote(reservation) -> tuple[str, str, object]:
    """(offer, kind of third party, host id) of a stay: hotel or individual host."""
    hote_id = tarifs._annonce(reservation)['host_id']
    conditions = tarifs.conditions(hote_id)
    if conditions and conditions.categorie == 'hotel':
        return 'HOTEL', 'hotel', hote_id
    return 'COURTE_DUREE', 'hote', hote_id


def offre_sejour(reservation) -> str:
    return _hote(reservation)[0]


def nature_commission(reservation) -> str:
    return 'R03' if _hote(reservation)[1] == 'hotel' else 'R02'


def parts_sejour(reservation) -> list[Part]:
    """Split of a stay paid (FIN-03.1): the nights and the cleaning are the host's money, the service fees
    Kwa-Ba's. The commission stays in the host's money until the arrival."""
    montants = tarifs.montants_de(reservation)
    _, tiers_type, hote_id = _hote(reservation)
    return [Part('T01', montants.prix_nuits, tiers_type, hote_id), Part('T02', montants.frais_menage, tiers_type, hote_id),
            Part('R01', montants.frais_service)]


def commission_a_l_arrivee(reservation, paiement) -> list[int]:
    """At the traveller's arrival the commission is acquired: it leaves the host's money for Kwa-Ba's revenue."""
    if not dans_le_grand_livre('reservation', reservation.pk):
        return []
    montants = tarifs.montants_de(reservation)
    _, tiers_type, hote_id = _hote(reservation)
    parts = [Part('T01', montants.commission_hote, tiers_type, hote_id, finance.SORTIE),
             Part(nature_commission(reservation), montants.commission_hote)]
    return ecrire(paiement, offre_sejour(reservation), parts, origine='arrivee', cle=f'arrivee:{reservation.pk}')


def annulation_sejour(reservation, paiement, bareme, *, commission_constatee: bool) -> None:
    """A paid stay cancelled: what is given back leaves the host's money and, if they are refunded, the fees; Kwa-Ba's
    share of the kept nights goes to R08 (case FF-02); the host keeps the kept nights minus that share. The refund
    itself is then owed to the traveller (du_au_voyageur). `commission_constatee`: the arrival already moved the
    commission to Kwa-Ba's revenue."""
    if not dans_le_grand_livre('reservation', reservation.pk):
        return
    montants = tarifs.montants_de(reservation)
    offre, tiers_type, hote_id = _hote(reservation)
    motif = f'Annulation de {reservation.reference}'
    if commission_constatee:
        finance.rectifier(nature_commission(reservation), 0, motif=motif, origine='annulation',
                          reservation_id=reservation.pk)
    du_hote = montants.prix_nuits - (montants.commission_hote if commission_constatee else 0)
    garde_hote = bareme.nuits_retenues - bareme.commission_hote
    frais_rendus = bareme.rembourse_voyageur - (montants.prix_nuits - bareme.nuits_retenues) - montants.frais_menage
    ecrire(paiement, offre, [
        Part('T02', montants.frais_menage, tiers_type, hote_id, finance.SORTIE),
        Part('T01', du_hote - garde_hote, tiers_type, hote_id, finance.SORTIE),
        Part('R08', bareme.commission_hote),
    ], origine='annulation', cle=f'annulation:{reservation.pk}')
    if frais_rendus > 0:
        finance.rectifier('R01', montants.frais_service - frais_rendus, motif=motif, origine='annulation',
                          reservation_id=reservation.pk)


def versement_hote_envoye(versement, paiement) -> None:
    """The payout to the host left: T09 settles what Kwa-Ba owed them."""
    from apps.reservations import api as reservations  # local import: reservations depends on paiements

    reservation = reservations.objet(versement.reservation_id)
    if reservation is None or not dans_le_grand_livre('reservation', reservation.pk):
        return
    offre, tiers_type, hote_id = _hote(reservation)
    ecrire(paiement, offre, [Part('T09', versement.montant, tiers_type, hote_id, finance.SORTIE)],
           origine='versement', cle=versement.payout_id or f'versement:{versement.pk}')


def frais_rectifies(reservation, nouveaux_frais: int, motif: str) -> None:
    """Service fees lowered after the payment (Stay Pack + Driver): R01 is brought to the new amount; the difference
    is then refunded (du_au_voyageur)."""
    if not dans_le_grand_livre('reservation', reservation.pk):
        return
    finance.rectifier('R01', nouveaux_frais, motif=motif, origine='frais_reduits', reservation_id=reservation.pk)
