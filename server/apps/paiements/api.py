from decimal import Decimal

from apps.users import api as users

from . import grand_livre, notifications, tarifs
from .documents import recu_paiement
from .models import ConditionsHoteModel, PaiementModel, ProfilVersementModel, RemboursementModel
from .operateurs import OPERATEUR_CHOICES, PAYS_CHOICES, operateurs_du_pays
from .paypal import FCFA_PAR_EURO
from .registre import ProduitPaye, Relance, enregistrer as enregistrer_produit
from .services import (
    INDISPONIBLE, PaiementErreur, annuler_paiement_reservation, creer_paiement, delai_paiement, envoyer_payout,
    fedapay_actif, indiquer_numero_remboursement, moyens_actifs, paiement_actif, planifier_versement_hote, rembourser,
    reservation_possible,
    synchroniser_paiement, synchroniser_payout,
)
from .views import CompteRemboursementSerializer

__all__ = [
    'a_profil_versement', 'titulaire_versement', 'FONDATEURS_MAX', 'conditions_commission', 'modifier_conditions_hote', 'operateurs_du_pays', 'ProduitPaye', 'Relance', 'enregistrer_produit', 'autre_paiement_reussi', 'etats_paiement', 'etats_pour_serializer',
    'ids_paiements_echoues', 'numero_remboursement_requis', 'synchroniser_dernier_paiement',
    'synchroniser_paiements_en_attente', 'CompteRemboursementSerializer', 'annuler_paiement_reservation', 'planifier_versement_hote', 'FCFA_PAR_EURO', 'INDISPONIBLE', 'OPERATEUR_CHOICES', 'PAYS_CHOICES',
    'PaiementErreur', 'alerte_admin', 'date_fr', 'commission_hote', 'conditions_hote', 'creer_paiement', 'delai_paiement',
    'documents_joints', 'emails_admins', 'envoyer_email', 'envoyer_payout', 'fcfa', 'fedapay_actif', 'frais_voyageur',
    'indiquer_numero_remboursement', 'moyens_actifs', 'paiement_actif', 'paiement_reussi', 'recu_pdf', 'rembourser',
    'reservation_possible', 'synchroniser_paiement', 'synchroniser_payout', 'texte_politique', 'total_sejour',
    'devis_sejour', 'frais_reduits', 'frais_reduits_sejour', 'montants_de', 'hotes_deja_visites', 'rembourser_en_partie',
    'paye_par_un_tiers', 'statut_paiement_de',
    # Ledger of the finance module (grand_livre.py)
    'arrivee', 'commission_a_l_arrivee', 'encaisser_sejour', 'frais_rectifies', 'offre_sejour',
]

arrivee = tarifs.arrivee
offre_sejour = grand_livre.offre_sejour
frais_rectifies = grand_livre.frais_rectifies


def encaisser_sejour(paiement, reservation) -> None:
    """Ledger: the split of a stay paid and confirmed, in the payment's transaction."""
    grand_livre.encaisser(paiement, grand_livre.parts_sejour(reservation))


def commission_a_l_arrivee(reservation) -> bool:
    """Ledger: at the arrival, the commission of a paid stay becomes Kwa-Ba's revenue. False if never paid online."""
    paiement = _paiement_reussi('reservation', reservation.pk)
    if paiement is None:
        return False
    grand_livre.commission_a_l_arrivee(reservation, paiement)
    return True

# Emails of the products paid online (stays, transfers, rentals, donations): same sending rules as the payment emails
envoyer_email = notifications._envoyer
emails_admins = notifications._admins
fcfa = notifications._fcfa
date_fr = notifications._date
documents_joints = notifications._documents
alerte_admin = notifications.alerte_admin


def total_sejour(prix_par_nuit: Decimal, nuits: int, type_annonce: str | None = None) -> int:
    """Standard total of a stay (6 % fees), with the cleaning fee of the listing's type."""
    return tarifs.calculer(prix_par_nuit, nuits, menage=tarifs.frais_menage(type_annonce)).total


def _paiement_reussi(type_objet: str, objet_id) -> PaiementModel | None:
    return (PaiementModel.objects.filter(**{f'{type_objet}_id': objet_id}, statut='reussi').order_by('cree_le').first())


def paiement_reussi(type_objet: str, objet_id) -> bool:
    """`type_objet`: reservation, transfert, location or don."""
    return _paiement_reussi(type_objet, objet_id) is not None


def statut_paiement_de(type_objet: str, objet_id, payeur_id) -> str | None:
    """Status of the last payment this third party started for the object (None if they never started one)."""
    dernier = (PaiementModel.objects.filter(**{f'{type_objet}_id': objet_id}, payeur_id=payeur_id)
               .order_by('-cree_le').values_list('statut', flat=True).first())
    return dernier


def paye_par_un_tiers(type_objet: str, objet_id):
    """The third party who paid the object (None if the traveller paid it, or if it is not paid)."""
    paiement = _paiement_reussi(type_objet, objet_id)
    return paiement.payeur if paiement and paiement.payeur_id else None


def recu_pdf(type_objet: str, objet_id) -> bytes | None:
    paiement = _paiement_reussi(type_objet, objet_id)
    return recu_paiement(paiement) if paiement else None


def texte_politique(reservation) -> str:
    return tarifs.texte_politique(reservation)


def frais_voyageur() -> Decimal:
    return tarifs.reglages().frais_voyageur


def commission_hote() -> Decimal:
    return tarifs.reglages().commission_particulier


def conditions_hote(hote_id) -> dict | None:
    """Category of the host (individual or hotel) and their Founders Programme dates, or None."""
    c = ConditionsHoteModel.objects.filter(hote_id=hote_id).first()
    if not c:
        return None
    return {'categorie': c.categorie, 'fondateur_debut': c.fondateur_debut, 'fondateur_fin': c.fondateur_fin}


def hotes_fondateurs(hote_ids) -> set:
    """Hosts of the Founders Programme (first 50 individual hosts): the title stays after their 6 months at 5 %."""
    return set(ConditionsHoteModel.objects.filter(
        hote_id__in=list(hote_ids), categorie='particulier', fondateur_debut__isnull=False,
    ).values_list('hote_id', flat=True))


def frais_reduits_sejour(prix_nuits: int) -> int:
    """Service fees of a stay at the reduced rate (loyal customer, Stay Pack + Driver)."""
    return tarifs.arrondi(Decimal(prix_nuits) * tarifs.reglages().frais_reduits)


def rembourser_en_partie(type_objet: str, objet_id, montant: int, motif: str) -> bool:
    """Refunds part of the successful payment of the object; False if it was never paid."""
    paiement = _paiement_reussi(type_objet, objet_id)
    if not paiement:
        return False
    rembourser(paiement, montant, motif)
    return True


def frais_reduits() -> Decimal:
    return tarifs.reglages().frais_reduits


def hotes_deja_visites(voyageur) -> set:
    """Hosts the traveller already stayed with (loyal customer rate)."""
    return tarifs.hotes_deja_visites(voyageur)


def devis_sejour(prix_par_nuit, hote_id, nuits: int, voyageur=None, nb_unites: int = 1,
                 type_annonce: str | None = None) -> tarifs.Montants:
    """Amounts of a stay with the rates of this host and this traveller, and the cleaning fee of the listing's type."""
    return tarifs.devis(prix_par_nuit, hote_id, nuits, voyageur=voyageur, nb_unites=nb_unites, type_annonce=type_annonce)


def frais_menage(type_annonce: str | None) -> int:
    return tarifs.frais_menage(type_annonce)


def montants_de(reservation, prix_par_nuit=None) -> tarifs.Montants:
    """Frozen amounts of a booking."""
    return tarifs.montants_de(reservation, prix_par_nuit)


def _par_objet(type_objet: str, objet_ids) -> dict:
    return {f'{type_objet}_id__in': list(objet_ids)}


def commission_hotel() -> Decimal:
    return tarifs.reglages().commission_hotel


def commission_fondateur() -> Decimal:
    return tarifs.reglages().commission_fondateur


def grille_menage() -> dict[str, int]:
    """Cleaning fee of every listing type (FCFA)."""
    return tarifs.grille_menage()


def commission_transfert() -> Decimal:
    """Share of an airport transfer kept by Kwa-Ba, set by the team."""
    return tarifs.reglages().commission_transfert


def mouvements(type_objet: str, objet_id) -> dict:
    """Every money movement of one object (back-office detail): payments, refunds and, for a stay, the host's payout."""
    from .models import VersementModel

    filtre = _par_objet(type_objet, [objet_id])
    paiements = [{
        'id': str(p.id), 'reference': p.reference, 'montant': p.montant, 'prestataire': p.prestataire, 'mode': p.mode,
        'statut': p.statut, 'cree_le': p.cree_le,
    } for p in PaiementModel.objects.filter(**filtre).order_by('cree_le')]
    remboursements = [{
        'id': str(r.id), 'montant': r.montant, 'motif': r.motif, 'statut': r.statut, 'cree_le': r.cree_le,
        'envoye_le': r.envoye_le,
    } for r in RemboursementModel.objects.filter(**filtre).order_by('cree_le')]
    versement = None
    if type_objet == 'reservation':
        v = VersementModel.objects.filter(reservation_id=objet_id).first()
        if v:
            versement = {'montant_brut': v.montant_brut, 'commission': v.commission, 'montant': v.montant,
                         'statut': v.statut, 'date_prevue': v.date_prevue, 'envoye_le': v.envoye_le}
    return {'paiements': paiements, 'remboursements': remboursements, 'versement': versement}


def etats_paiement(type_objet: str, objet_ids) -> dict:
    """Per object: status of its last payment (None if none) and its refunds ({'montant', 'statut'} or None)."""
    objet_ids = list(objet_ids)
    champ = f'{type_objet}_id'
    etats = {i: {'paiement': None, 'remboursement': None} for i in objet_ids}
    for p in PaiementModel.objects.filter(**_par_objet(type_objet, objet_ids)).order_by('cree_le').values(champ, 'statut'):
        etats[p[champ]]['paiement'] = p['statut']
    if type_objet == 'don':
        return etats
    lignes = {}
    for r in RemboursementModel.objects.filter(**_par_objet(type_objet, objet_ids)).values(champ, 'statut', 'montant'):
        lignes.setdefault(r[champ], []).append(r)
    for objet_id, siennes in lignes.items():
        if any(r['statut'] == 'attente_numero' for r in siennes):
            statut = 'attente_numero'
        else:
            statut = 'envoye' if all(r['statut'] == 'envoye' for r in siennes) else 'en_cours'
        etats[objet_id]['remboursement'] = {'montant': sum(r['montant'] for r in siennes), 'statut': statut}
    return etats


def etats_pour_serializer(serializer, type_objet: str) -> dict:
    """etats_paiement of the objects being serialized (one or a list), read once for the whole list."""
    cle = f'_etats_paiement_{type_objet}'
    if cle not in serializer.context:
        instance = serializer.parent.instance if serializer.parent is not None else serializer.instance
        objets = list(instance) if isinstance(instance, (list, tuple)) or hasattr(instance, 'model') else [instance]
        serializer.context[cle] = etats_paiement(type_objet, [o.pk for o in objets])
    return serializer.context[cle]


def numero_remboursement_requis(type_objet: str, objet_id) -> bool:
    """A refund waits for the Mobile Money account the traveller must give."""
    return RemboursementModel.objects.filter(**{f'{type_objet}_id': objet_id}, statut='attente_numero').exists()


def synchroniser_dernier_paiement(type_objet: str, objet_id) -> bool:
    """Return page after payment: the last payment is read again at the provider if it is pending.
    Returns True if it was."""
    dernier = PaiementModel.objects.filter(**{f'{type_objet}_id': objet_id}).order_by('-cree_le').first()
    if dernier and dernier.statut == 'en_attente':
        synchroniser_paiement(dernier)
        return True
    return False


def synchroniser_paiements_en_attente(type_objet: str, objet_id) -> None:
    """Last check at the provider before an expiry."""
    for paiement in PaiementModel.objects.filter(**{f'{type_objet}_id': objet_id}, statut='en_attente'):
        synchroniser_paiement(paiement)


def autre_paiement_reussi(type_objet: str, objet_id, paiement) -> bool:
    """Another successful payment than `paiement` exists for the object (paid twice)."""
    return (PaiementModel.objects.filter(**{f'{type_objet}_id': objet_id}, statut='reussi')
            .exclude(pk=paiement.pk).exists())


def ids_paiements_echoues(type_objet: str) -> set:
    """Objects whose payments all failed or were cancelled (none pending nor successful)."""
    champ = f'{type_objet}_id'
    echoues = set(PaiementModel.objects.filter(**{f'{champ}__isnull': False}, statut__in=('echoue', 'annule'))
                  .values_list(champ, flat=True))
    actifs = set(PaiementModel.objects.filter(**{f'{champ}__in': echoues}, statut__in=('en_attente', 'reussi'))
                 .values_list(champ, flat=True))
    return echoues - actifs


FONDATEURS_MAX = 50


def conditions_commission(hote) -> dict:
    """Host's commission: category, Founders Programme and rate applied today."""
    c = tarifs.conditions(hote)
    return {
        'categorie': c.categorie if c else 'particulier',
        'fondateur_debut': c.fondateur_debut if c else None,
        'fondateur_fin': c.fondateur_fin if c else None,
        'commission_pourcent': float(tarifs.taux_commission(hote) * 100),
    }


def modifier_conditions_hote(hote, valeurs, par) -> str | None:
    """Category (individual, hotel) and Founders Programme dates of a host, set by an administrator.
    Returns an error message, or None once saved."""
    from django.utils.dateparse import parse_date

    if not users.hote_ou_candidat(hote) or not isinstance(valeurs, dict):
        return "Seul un hôte a des conditions de commission."
    categorie = valeurs.get('categorie', 'particulier')
    if categorie not in dict(ConditionsHoteModel.CATEGORIES):
        return "Catégorie inconnue."
    debut, fin = (parse_date(str(valeurs.get(c) or '')) or None for c in ('fondateur_debut', 'fondateur_fin'))
    if bool(debut) != bool(fin):
        return "Indiquez le début et la fin du Programme Fondateurs, ou aucun des deux."
    if debut and fin <= debut:
        return "La fin du Programme Fondateurs doit être après son début."
    if debut and categorie == 'hotel':
        return "Le Programme Fondateurs concerne les hôtes particuliers."
    if debut and not ConditionsHoteModel.objects.filter(hote_id=hote.pk, fondateur_debut__isnull=False).exists() \
            and ConditionsHoteModel.objects.filter(fondateur_debut__isnull=False).count() >= FONDATEURS_MAX:
        return f"Le Programme Fondateurs est limité aux {FONDATEURS_MAX} premiers hôtes."
    ConditionsHoteModel.objects.update_or_create(hote_id=hote.pk, defaults={
        'categorie': categorie, 'fondateur_debut': debut, 'fondateur_fin': fin, 'mis_a_jour_par_id': getattr(par, 'pk', None)})
    return None


def a_profil_versement(hote_id) -> bool:
    return ProfilVersementModel.objects.filter(hote_id=hote_id).exists()


def titulaire_versement(hote_id) -> str:
    """Name on the host's Mobile Money account: the agent compares it with the identity document."""
    return ProfilVersementModel.objects.filter(hote_id=hote_id).values_list('titulaire', flat=True).first() or ''
