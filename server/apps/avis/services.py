from datetime import timedelta

from django.db.models import Avg, Count
from django.utils import timezone

from apps.hebergements.models import HebergementModel
from apps.reservations.models import ReservationModel

# Time allowed to leave a review after departure (beyond it, memories are no longer reliable)
DELAI_AVIS_JOURS = 14


def motif_refus(reservation: ReservationModel, user) -> str | None:
    """Returns the reason why the user cannot review this stay, or None if they can."""
    today = timezone.localdate()
    if reservation.guest_id != user.id:
        return "Seul le voyageur qui a séjourné peut laisser un avis."
    if reservation.status != 'confirmed':
        return "Seuls les séjours confirmés peuvent être évalués."
    if reservation.check_out > today:
        return "Vous pourrez laisser un avis après votre départ."
    if reservation.check_out < today - timedelta(days=DELAI_AVIS_JOURS):
        return f"Le délai de {DELAI_AVIS_JOURS} jours pour évaluer ce séjour est dépassé."
    if hasattr(reservation, 'avis'):
        return "Vous avez déjà laissé un avis pour ce séjour."
    return None


def sejours_a_evaluer(user):
    today = timezone.localdate()
    return (
        ReservationModel.objects
        .filter(
            guest=user,
            status='confirmed',
            check_out__lte=today,
            check_out__gte=today - timedelta(days=DELAI_AVIS_JOURS),
            avis__isnull=True,
        )
        .select_related('hebergement')
        .order_by('-check_out')
    )


def recalculer_note(hebergement_id) -> None:
    """The displayed rating and the number of reviews only come from verified reviews."""
    stats = HebergementModel.objects.filter(pk=hebergement_id).aggregate(
        moyenne=Avg('avis__note'), total=Count('avis'),
    )
    HebergementModel.objects.filter(pk=hebergement_id).update(
        rating=round(stats['moyenne'] or 0, 2),
        review_count=stats['total'],
    )
