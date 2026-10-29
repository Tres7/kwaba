"""Life cycle of a booking's money.

Collection: FedaPay (Mobile Money, Visa/Mastercard card) or PayPal (in euros).
Payouts to hosts: always FedaPay (Mobile Money).

    "pending" booking (dates held 30 min)
        → successful FedaPay payment → "confirmed" booking + payout scheduled (arrival + 24 h)
        → the worker (manage.py traiter_paiements) sends the payout to the host when due
    cancellation → refund of the traveller according to the scale, payout reduced or cancelled

Golden rule: never trust the browser nor the content of a webhook. The status of a
transaction is always read again from FedaPay before acting.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from config import prelancement

from . import fedapay, paypal, tarifs
from .models import PaiementModel, ProfilVersementModel, RemboursementModel, VersementModel
from .registre import PRODUITS

logger = logging.getLogger('apps.paiements')

MAX_TENTATIVES = 5
# Delay before a new try after a failure: 15 min, 30 min, 1 h, 2 h (then manual handling)
DELAI_NOUVEL_ESSAI = timedelta(minutes=15)


def _peut_reessayer(ligne) -> bool:
    if not ligne.tentatives:
        return True
    attente = DELAI_NOUVEL_ESSAI * (2 ** (ligne.tentatives - 1))
    return timezone.now() - ligne.mis_a_jour_le >= attente


class PaiementErreur(Exception):
    """Error whose message can be shown as is to the user."""


INDISPONIBLE = "Le paiement en ligne est momentanément indisponible : la réservation n'est pas possible pour l'instant. Réessayez un peu plus tard."


# Method chosen by the traveller → provider that collects
MOYENS = {
    'mobile_money': 'fedapay',
    'carte': 'fedapay',
    'paypal': 'paypal',
}


def delai_paiement() -> timedelta:
    """Time given to pay a booking, a transfer or a rental: their dates are held meanwhile."""
    return timedelta(minutes=settings.FEDAPAY['EXPIRATION_MINUTES'])


def fedapay_actif() -> bool:
    return bool(settings.FEDAPAY['SECRET_KEY'])


def paypal_actif() -> bool:
    # PayPal is not open at launch: offered only with the switch of the not-yet-open methods
    return bool(settings.PAYPAL['CLIENT_ID'] and settings.PAYPAL['CLIENT_SECRET']
                and settings.MODULES['paiements_non_ouverts'])


def moyens_actifs() -> list[str]:
    actifs = {'fedapay': fedapay_actif(), 'paypal': paypal_actif()}
    return [moyen for moyen, prestataire in MOYENS.items() if actifs[prestataire]]


def paiement_actif() -> bool:
    return fedapay_actif() or paypal_actif()


def reservation_possible() -> bool:
    """A booking is paid online; without a configured provider, only in development (PAIEMENT_HORS_LIGNE)."""
    return paiement_actif() or settings.PAIEMENT_HORS_LIGNE


# --- Encaissement ------------------------------------------------------------------------

def creer_paiement(*, type_objet: str, objet_id, montant: int, moyen: str, description: str, url_retour: str,
                   voyageur) -> str:
    """Creates the transaction at the provider for the object (booking, transfer, rental or donation) and returns
    the address of the payment page. `url_retour`: page of the site the traveller comes back to."""
    # Backstop: the views already refuse in pre-launch mode, no payment may ever be created before the opening
    if prelancement.actif():
        raise PaiementErreur(prelancement.MESSAGE)
    if moyen not in moyens_actifs():
        raise PaiementErreur("Ce moyen de paiement n'est pas disponible.")
    cible = {f'{type_objet}_id': objet_id}

    if MOYENS[moyen] == 'paypal':
        paiement = PaiementModel(**cible, montant=montant, prestataire='paypal', montant_eur=paypal.en_euros(montant))
        try:
            paiement.transaction_id, paiement.url_paiement = paypal.client().creer_commande(
                montant_eur=paiement.montant_eur, description=description, reference=str(paiement.id),
                url_retour=url_retour, url_annulation=f"{url_retour}?annule=1",
            )
        except paypal.PayPalErreur:
            logger.exception("Création de la commande PayPal impossible pour %s", objet_id)
            raise PaiementErreur("PayPal est momentanément indisponible. Réessayez ou choisissez un autre moyen de paiement.")
        paiement.save()
        return paiement.url_paiement

    try:
        transaction_id, url = fedapay.client().creer_transaction(
            montant=montant, description=description, callback_url=url_retour,
            client={
                'firstname': voyageur.first_name or 'Voyageur',
                'lastname': voyageur.last_name or 'Kwa-Ba',
                'email': voyageur.email,
            },
        )
    except fedapay.FedaPayErreur:
        logger.exception("Création de la transaction impossible pour %s", objet_id)
        raise PaiementErreur("Le service de paiement est momentanément indisponible. Réessayez dans quelques instants.")
    PaiementModel.objects.create(**cible, montant=montant, transaction_id=transaction_id, url_paiement=url)
    return url


def synchroniser_paiement(paiement: PaiementModel) -> str:
    """Reads the transaction again at the provider and applies its status. Returns the up-to-date internal status."""
    if paiement.statut != 'en_attente' or not paiement.transaction_id:
        return paiement.statut
    if paiement.prestataire == 'paypal':
        return _synchroniser_paypal(paiement)
    try:
        donnees = fedapay.client().lire_transaction(paiement.transaction_id)
    except fedapay.FedaPayErreur:
        return paiement.statut

    nouveau = fedapay.STATUTS_TRANSACTION.get(str(donnees.get('status', '')).lower())
    if nouveau == 'reussi':
        _paiement_reussi(paiement.pk, donnees)
    elif nouveau:
        PaiementModel.objects.filter(pk=paiement.pk, statut='en_attente').update(statut=nouveau)
    paiement.refresh_from_db()
    return paiement.statut


def _synchroniser_paypal(paiement: PaiementModel) -> str:
    """Order approved by the traveller (APPROVED) → it is captured; COMPLETED → successful payment."""
    try:
        api = paypal.client()
        commande = api.lire_commande(paiement.transaction_id)
        if commande.get('status') == 'APPROVED':
            commande = api.capturer(paiement.transaction_id)
    except paypal.PayPalErreur:
        return paiement.statut

    nouveau = paypal.STATUTS_COMMANDE.get(commande.get('status'))
    if nouveau == 'reussi':
        PaiementModel.objects.filter(pk=paiement.pk).update(capture_id=paypal.id_capture(commande))
        _paiement_reussi(paiement.pk, {'mode': 'paypal'})
    elif nouveau:
        PaiementModel.objects.filter(pk=paiement.pk, statut='en_attente').update(statut=nouveau)
    paiement.refresh_from_db()
    return paiement.statut


def _telephone(donnees: dict) -> tuple[str, str]:
    """Charged number (used for refunds), when FedaPay provides it."""
    for source in (donnees.get('payment_method'), (donnees.get('customer') or {}).get('phone_number')):
        if isinstance(source, dict) and source.get('number'):
            return str(source['number']), str(source.get('country') or '')[:2].upper()
    return '', ''


def _paiement_reussi(paiement_id, donnees: dict):
    with transaction.atomic():
        paiement = PaiementModel.objects.select_for_update().get(pk=paiement_id)
        if paiement.statut == 'reussi':
            return  # already processed (webhook received twice, or webhook + browser check)

        paiement.statut = 'reussi'
        paiement.mode = str(donnees.get('mode') or '')[:40]
        if paiement.prestataire == 'fedapay':
            paiement.telephone, paiement.pays_telephone = _telephone(donnees)
        paiement.save()
        logger.info("Paiement reçu : %s FCFA pour %s", paiement.montant, paiement.reference)

        # The module of the paid object handles it (confirmation, refund if paid twice or cancelled meanwhile…)
        PRODUITS[paiement.type_objet].paiement_recu(paiement)


def planifier_versement_hote(reservation):
    """Payout to the host of a paid stay (arrival + 24 h), from the booking's frozen amounts."""
    montants = tarifs.montants_de(reservation)
    VersementModel.objects.update_or_create(
        reservation_id=reservation.id,
        defaults={
            'hote_id': tarifs._annonce(reservation)['host_id'],
            'montant_brut': montants.prix_nuits,
            'commission': montants.commission_hote,
            'montant': montants.montant_hote,
            'date_prevue': tarifs.date_versement(reservation),
            'statut': 'planifie',
        },
    )


def _par_carte(paiement) -> bool:
    return paiement.description['moyen'] == 'carte' or 'card' in paiement.mode.lower()


def rembourser(paiement, montant: int, motif: str):
    """Schedules the refund of `montant` on this payment (then sent by the worker)."""
    if montant <= 0:
        return None
    logger.info("Remboursement de %s FCFA prévu pour %s : %s", montant, paiement.reference, motif)
    statut = 'a_envoyer'
    if paiement.prestataire == 'fedapay' and not paiement.telephone and not _par_carte(paiement):
        # Mobile Money: FedaPay does not give the charged number, it is asked to the traveller
        statut = 'attente_numero'
    return RemboursementModel.objects.create(
        reservation_id=paiement.reservation_id, transfert_id=paiement.transfert_id, location_id=paiement.location_id,
        paiement=paiement, montant=montant, motif=motif, statut=statut,
    )


def indiquer_numero_remboursement(type_objet: str, objet_id, pays: str, operateur: str, numero: str) -> int:
    """Saves the traveller's Mobile Money account on the pending refunds of the object
    (booking, transfer or rental). Returns their number."""
    return RemboursementModel.objects.filter(**{f'{type_objet}_id': objet_id}, statut='attente_numero').update(
        pays=pays, operateur=operateur, numero=numero, statut='a_envoyer', derniere_erreur='',
    )


# --- Annulation --------------------------------------------------------------------------

def annuler_paiement_reservation(reservation, par: str) -> int:
    """Money of a cancelled stay: the traveller's refund according to the scale, the host's payout reduced or
    cancelled. `par`: voyageur, hote or plateforme. Returns the amount refunded (0 if never paid)."""
    paiement = PaiementModel.objects.filter(reservation_id=reservation.id, statut='reussi').order_by('cree_le').first()
    if not paiement:
        return 0
    montants = tarifs.montants_de(reservation)
    if par == 'voyageur':
        bareme = tarifs.bareme_voyageur(montants, reservation)
        motif = "Annulation par le voyageur"
    else:
        bareme = tarifs.Annulation(rembourse_voyageur=montants.total, nuits_retenues=0)
        motif = "Annulation par l'hôte" if par == 'hote' else "Annulation par Kwa-Ba"

    versement = VersementModel.objects.select_for_update().filter(reservation_id=reservation.id).first()
    if versement and versement.statut in ('planifie', 'echoue'):
        if bareme.nuits_retenues:
            versement.montant_brut = bareme.nuits_retenues
            versement.commission = bareme.commission_hote
            versement.montant = bareme.montant_hote
            versement.statut = 'planifie'
        else:
            versement.statut = 'annule'
        versement.save()
    elif versement and versement.statut in ('en_cours', 'envoye'):
        logger.warning("Annulation de %s après le versement à l'hôte : à régulariser", reservation.reference)

    rembourser(paiement, bareme.rembourse_voyageur, motif)
    return bareme.rembourse_voyageur


# --- Payouts and refunds (worker) -----------------------------------------------

def _client_payout(utilisateur, numero: str, pays: str, titulaire: str = '') -> dict:
    prenom, _, nom = (titulaire or '').strip().partition(' ')
    return {
        'firstname': prenom or utilisateur.first_name or 'Client',
        'lastname': nom or utilisateur.last_name or 'Kwa-Ba',
        'email': utilisateur.email,
        'phone_number': {'number': numero, 'country': pays.lower()},
    }


def _reserver(modele, pk, de: str) -> bool:
    """Takes hold of a row (avoids a double sending if two workers run)."""
    return modele.objects.filter(pk=pk, statut=de).update(statut='en_cours') == 1


def envoyer_payout(ligne, *, mode: str, numero: str, pays: str, email: str, titulaire: str) -> bool:
    """Sends a Mobile Money payout for a scheduled row (payout to a host or to a driver).

    The row must have the fields statut, tentatives, payout_id, mode, numero, derniere_erreur.
    Returns True if FedaPay accepted the sending.
    """
    if not _peut_reessayer(ligne) or not _reserver(type(ligne), ligne.pk, 'planifie'):
        return False
    prenom, _, nom = titulaire.strip().partition(' ')
    ligne.tentatives += 1
    try:
        ligne.payout_id = fedapay.client().creer_versement(montant=ligne.montant, mode=mode, client={
            'firstname': prenom or 'Client', 'lastname': nom or 'Kwa-Ba', 'email': email,
            'phone_number': {'number': numero, 'country': pays.lower()},
        })
        ligne.statut, ligne.derniere_erreur = 'en_cours', ''
        ligne.mode, ligne.numero = mode, numero
    except fedapay.FedaPayErreur as exc:
        ligne.derniere_erreur = str(exc)
        ligne.statut = 'echoue' if ligne.tentatives >= MAX_TENTATIVES else 'planifie'
    ligne.save()
    return ligne.statut == 'en_cours'


def synchroniser_payout(ligne):
    """Reads again from FedaPay the status of an ongoing payout (host or driver)."""
    try:
        donnees = fedapay.client().lire_versement(ligne.payout_id)
    except fedapay.FedaPayErreur:
        return
    statut = fedapay.STATUTS_PAYOUT.get(str(donnees.get('status', '')).lower())
    if statut == 'envoye':
        ligne.statut, ligne.envoye_le = 'envoye', timezone.now()
        logger.info("Versement de %s FCFA envoyé (%s)", ligne.montant, ligne.pk)
    elif statut == 'echoue':
        ligne.derniere_erreur = str(donnees.get('last_error_code') or 'Versement refusé par FedaPay')
        ligne.statut = 'echoue' if ligne.tentatives >= MAX_TENTATIVES else 'planifie'
    else:
        return
    ligne.save()


def envoyer_versements_dus() -> int:
    if not fedapay_actif():
        return 0  # payouts to hosts go through FedaPay
    envoyes = 0
    from apps.reservations import api as reservations  # local import: reservations depends on paiements

    dus = list(VersementModel.objects.filter(statut='planifie', date_prevue__lte=timezone.now()).select_related('hote'))
    confirmees = reservations.ids_confirmees(v.reservation_id for v in dus)
    for versement in [v for v in dus if v.reservation_id in confirmees][:50]:
        profil = ProfilVersementModel.objects.filter(hote=versement.hote).first()
        if not profil:
            if not versement.derniere_erreur:
                versement.derniere_erreur = "L'hôte n'a pas encore indiqué où recevoir son argent."
                versement.save(update_fields=['derniere_erreur', 'mis_a_jour_le'])
            continue
        envoyes += envoyer_payout(
            versement, mode=profil.operateur, numero=profil.numero, pays=profil.pays,
            email=versement.hote.email, titulaire=profil.titulaire or versement.hote.get_full_name(),
        )
    return envoyes


def synchroniser_versement(versement: VersementModel):
    synchroniser_payout(versement)


def envoyer_remboursements() -> int:
    envoyes = 0
    for remboursement in RemboursementModel.objects.filter(statut='a_envoyer').select_related('paiement')[:50]:
        if not _peut_reessayer(remboursement):
            continue
        paiement = remboursement.paiement
        if paiement.prestataire == 'paypal':
            envoyes += _rembourser_paypal(remboursement)
            continue
        # Account given by the traveller, otherwise charged number if known
        if remboursement.numero:
            mode, numero, pays = remboursement.operateur, remboursement.numero, remboursement.pays
        else:
            mode, numero, pays = paiement.mode, paiement.telephone, paiement.pays_telephone
        if not (mode and numero) or not fedapay_actif():
            # Bank card: manual refund from the FedaPay dashboard
            remboursement.statut = 'a_traiter'
            remboursement.derniere_erreur = "Paiement par carte ou compte inconnu : rembourser depuis le tableau de bord FedaPay."
            remboursement.save()
            continue
        if not _reserver(RemboursementModel, remboursement.pk, 'a_envoyer'):
            continue
        remboursement.tentatives += 1
        try:
            remboursement.payout_id = fedapay.client().creer_versement(
                montant=remboursement.montant, mode=mode,
                client=_client_payout(remboursement.payeur, numero, pays),
            )
            remboursement.statut, remboursement.derniere_erreur = 'en_cours', ''
            envoyes += 1
        except fedapay.FedaPayErreur as exc:
            remboursement.derniere_erreur = str(exc)
            remboursement.statut = 'a_traiter' if remboursement.tentatives >= MAX_TENTATIVES else 'a_envoyer'
        remboursement.save()
    return envoyes


def _rembourser_paypal(remboursement: RemboursementModel) -> int:
    """Refund to the traveller's card or PayPal account, pro rata in euros."""
    paiement = remboursement.paiement
    if not paiement.capture_id or not paypal_actif():
        remboursement.statut = 'a_traiter'
        remboursement.derniere_erreur = "Encaissement PayPal introuvable : rembourser depuis le compte PayPal."
        remboursement.save()
        return 0
    if not _reserver(RemboursementModel, remboursement.pk, 'a_envoyer'):
        return 0
    plafond = paiement.montant_eur or paypal.en_euros(paiement.montant)
    montant_eur = min(paypal.en_euros(remboursement.montant), plafond)
    remboursement.tentatives += 1
    try:
        reponse = paypal.client().rembourser(paiement.capture_id, montant_eur, reference=str(remboursement.id))
        remboursement.payout_id = reponse.get('id', '')
        if reponse.get('status') == 'COMPLETED':
            remboursement.statut, remboursement.envoye_le = 'envoye', timezone.now()
        else:
            remboursement.statut = 'en_cours'
        remboursement.derniere_erreur = ''
    except paypal.PayPalErreur as exc:
        remboursement.derniere_erreur = str(exc)
        remboursement.statut = 'a_traiter' if remboursement.tentatives >= MAX_TENTATIVES else 'a_envoyer'
    remboursement.save()
    return 1 if remboursement.statut in ('en_cours', 'envoye') else 0


def synchroniser_remboursement(remboursement: RemboursementModel):
    if remboursement.paiement.prestataire == 'paypal':
        try:
            statut = paypal.client().lire_remboursement(remboursement.payout_id).get('status')
        except paypal.PayPalErreur:
            return
        if statut == 'COMPLETED':
            remboursement.statut, remboursement.envoye_le = 'envoye', timezone.now()
            remboursement.save()
        elif statut in ('FAILED', 'CANCELLED'):
            remboursement.statut, remboursement.derniere_erreur = 'a_traiter', f"Remboursement PayPal {statut}"
            remboursement.save()
        return
    try:
        donnees = fedapay.client().lire_versement(remboursement.payout_id)
    except fedapay.FedaPayErreur:
        return
    statut = fedapay.STATUTS_PAYOUT.get(str(donnees.get('status', '')).lower())
    if statut == 'envoye':
        remboursement.statut, remboursement.envoye_le = 'envoye', timezone.now()
    elif statut == 'echoue':
        remboursement.statut = 'a_traiter'
        remboursement.derniere_erreur = str(donnees.get('last_error_code') or 'Remboursement refusé par FedaPay')
    else:
        return
    remboursement.save()


def passe() -> dict:
    """One pass of the worker. Also catches up on lost webhooks (and their absence locally)."""
    recents = PaiementModel.objects.filter(statut='en_attente', cree_le__gte=timezone.now() - timedelta(hours=2))[:50]
    for paiement in recents:
        synchroniser_paiement(paiement)
    for versement in VersementModel.objects.filter(statut='en_cours').exclude(payout_id='')[:50]:
        synchroniser_versement(versement)
    for remboursement in RemboursementModel.objects.filter(statut='en_cours').exclude(payout_id='').select_related('paiement')[:50]:
        synchroniser_remboursement(remboursement)
    from . import notifications  # local import: notifications imports the models and the rates

    stats = {
        'versements_envoyes': envoyer_versements_dus(),
        'remboursements_envoyes': envoyer_remboursements(),
    }
    for produit in PRODUITS.values():
        if produit.passe:
            stats.update(produit.passe())
    from . import relances
    # After the expiries: the "cancelled for lack of payment" email goes in the same pass
    stats['relances'] = relances.envoyer_relances()
    stats['emails'] = notifications.envoyer_notifications()
    return {k: v for k, v in stats.items() if v}


def traiter_evenement(evenement: dict):
    """FedaPay webhook: only the id is used, then the object is read again from FedaPay."""
    nom = str(evenement.get('name', ''))
    identifiant = str((evenement.get('entity') or {}).get('id', ''))
    if not identifiant:
        return
    if nom.startswith('transaction.'):
        paiement = PaiementModel.objects.filter(transaction_id=identifiant).first()
        if paiement:
            synchroniser_paiement(paiement)
    elif nom.startswith('payout.'):
        for versement in VersementModel.objects.filter(payout_id=identifiant, statut='en_cours'):
            synchroniser_versement(versement)
        for produit in PRODUITS.values():
            for versement in (produit.versements(identifiant) if produit.versements else []):
                synchroniser_payout(versement)
        for remboursement in RemboursementModel.objects.filter(payout_id=identifiant, statut='en_cours'):
            synchroniser_remboursement(remboursement)
