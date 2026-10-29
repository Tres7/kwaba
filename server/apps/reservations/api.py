import uuid
from collections.abc import Iterable
from datetime import date
from types import SimpleNamespace

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.users import api as users

from .models import ReservationModel


def appartient_au_voyageur(reservation_id: uuid.UUID, voyageur_id: uuid.UUID) -> bool:
    return ReservationModel.objects.filter(pk=reservation_id, guest_id=voyageur_id).exists()


def resumes(reservation_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, dict]:
    return {r.id: {
        'id': r.id, 'reference': r.reference, 'hebergement_id': r.hebergement_id, 'voyageur_id': r.guest_id,
        'check_in': r.check_in, 'check_out': r.check_out, 'voyageurs': r.guests_count, 'statut': r.status,
        'total': r.total_price,
    } for r in users.attacher(ReservationModel.objects.filter(pk__in=list(reservation_ids)), 'guest')}


def paires_confirmees(paires: Iterable[tuple[uuid.UUID, uuid.UUID]]) -> set[tuple[uuid.UUID, uuid.UUID]]:
    paires = set(paires)
    if not paires:
        return set()
    condition = Q()
    for hebergement_id, voyageur_id in paires:
        condition |= Q(hebergement_id=hebergement_id, guest_id=voyageur_id)
    return set(ReservationModel.objects.filter(condition, status='confirmed').values_list('hebergement_id', 'guest_id')) & paires


def confirmee_pour_hote(reservation_id: uuid.UUID, hote_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID] | None:
    return (ReservationModel.objects.filter(pk=reservation_id, hebergement_id__in=hebergements.ids_annonces_de(hote_id),
                                            status='confirmed')
            .values_list('hebergement_id', 'guest_id').first())


def sejours_termines(voyageur_id: uuid.UUID, depart_depuis: date, depart_jusqu_a: date) -> list[dict]:
    return [{
        'id': r.id, 'hebergement_id': r.hebergement_id, 'check_in': r.check_in, 'check_out': r.check_out,
    } for r in ReservationModel.objects.filter(guest_id=voyageur_id, status='confirmed', check_out__lte=depart_jusqu_a,
                                               check_out__gte=depart_depuis).order_by('-check_out')]


def reduire_frais_pack_sejour(reservation_id: uuid.UUID, voyageur_id: uuid.UUID) -> tuple[int, str]:
    """Stay Pack + Driver: an upcoming paid stay of this traveller gets service fees lowered to the reduced rate.
    Returns (amount to refund, booking reference); (0, '') if the stay is not eligible. To call in a transaction."""
    r = ReservationModel.objects.select_for_update().filter(pk=reservation_id).first()
    if not r or r.guest_id != voyageur_id or r.status != 'confirmed' or r.check_in <= timezone.localdate():
        return 0, ''
    if r.prix_nuits is None or r.frais_service is None:
        return 0, ''
    nouveaux_frais = paiements.frais_reduits_sejour(r.prix_nuits)
    ecart = r.frais_service - nouveaux_frais
    if ecart <= 0:
        return 0, ''
    r.frais_service, r.total_price = nouveaux_frais, r.prix_nuits + nouveaux_frais
    r.save(update_fields=['frais_service', 'total_price'])
    return ecart, r.reference


def nb_par_annonce(hebergement_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, int]:
    return dict(ReservationModel.objects.filter(hebergement_id__in=list(hebergement_ids)).values('hebergement_id')
                .annotate(n=Count('id')).values_list('hebergement_id', 'n'))


def nb_par_voyageur(voyageur_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, int]:
    return dict(ReservationModel.objects.filter(guest_id__in=list(voyageur_ids)).values('guest_id')
                .annotate(n=Count('id')).values_list('guest_id', 'n'))


def _objet(r: ReservationModel) -> SimpleNamespace:
    return SimpleNamespace(
        id=r.id, pk=r.pk, reference=r.reference, hebergement_id=r.hebergement_id, type_logement_id=r.type_logement_id,
        guest=r.guest, guest_id=r.guest_id, check_in=r.check_in, check_out=r.check_out, nights=r.nights,
        guests_count=r.guests_count, message=r.message, status=r.status, payment_method=r.payment_method,
        total_price=r.total_price, prix_nuits=r.prix_nuits, frais_service=r.frais_service,
        commission_hote=r.commission_hote, created_at=r.created_at, expire_le=r.expire_le, annule_par=r.annule_par,
    )


def objets(reservation_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, SimpleNamespace]:
    """Bookings as plain read-only objects (emails, payouts, earnings)."""
    return {r.id: _objet(r) for r in users.attacher(ReservationModel.objects.filter(pk__in=list(reservation_ids)), 'guest')}


def objet(reservation_id: uuid.UUID) -> SimpleNamespace | None:
    return objets([reservation_id]).get(reservation_id)


def ids_confirmees(reservation_ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    return set(ReservationModel.objects.filter(pk__in=list(reservation_ids), status='confirmed').values_list('pk', flat=True))


def hotes_deja_visites(voyageur) -> set:
    """Hosts the traveller has already stayed with through Kwa-Ba (paid and finished stay): loyal customer rate."""
    if not voyageur or not voyageur.is_authenticated:
        return set()
    sejours = (ReservationModel.objects.filter(guest_id=voyageur.pk, status='confirmed', check_out__lte=timezone.localdate())
               .values_list('hebergement_id', flat=True))
    return set(hebergements.hotes_des_annonces(set(sejours)).values())


def annuler(reservation, par: str) -> int:
    """Cancels the booking (voyageur, hote or plateforme) and refunds the traveller. Returns the refunded amount."""
    from .paiement import annuler as annuler_reservation

    return annuler_reservation(reservation, par)


def statistiques(depuis) -> dict:
    """Bookings made since `depuis` (datetime): confirmed, cancelled, and confirmed volume in FCFA."""
    resultat = ReservationModel.objects.filter(created_at__gte=depuis).aggregate(
        confirmees_30j=Count('id', filter=Q(status='confirmed')),
        annulees_30j=Count('id', filter=Q(status='cancelled')),
        volume_30j=Sum('total_price', filter=Q(status='confirmed')),
    )
    resultat['volume_30j'] = int(resultat['volume_30j'] or 0)
    return resultat


def confirmees_par_jour(premier_jour: date) -> dict:
    """Per day since `premier_jour`: number and volume of the confirmed bookings made that day."""
    return {
        ligne['jour']: ligne
        for ligne in ReservationModel.objects
        .filter(status='confirmed', created_at__date__gte=premier_jour)
        .annotate(jour=TruncDate('created_at'))
        .values('jour')
        .annotate(nombre=Count('id'), volume=Sum('total_price'))
    }
