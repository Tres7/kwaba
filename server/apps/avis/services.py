from datetime import timedelta

from django.db.models import Avg, Count
from django.utils import timezone

from apps.hebergements import api as hebergements
from apps.reservations import api as reservations

from .models import AvisModel

# Time allowed to leave a review after departure (beyond it, memories are no longer reliable)
DELAI_AVIS_JOURS = 14


def motif_refus(sejour: dict, user_id, deja_evalue: bool) -> str | None:
    """Returns the reason why the user cannot review this stay, or None if they can.

    `sejour`: summary of the booking (reservations.api.resumes)."""
    today = timezone.localdate()
    if sejour['voyageur_id'] != user_id:
        return "Seul le voyageur qui a séjourné peut laisser un avis."
    if sejour['statut'] != 'confirmed':
        return "Seuls les séjours confirmés peuvent être évalués."
    if sejour['check_out'] > today:
        return "Vous pourrez laisser un avis après votre départ."
    if sejour['check_out'] < today - timedelta(days=DELAI_AVIS_JOURS):
        return f"Le délai de {DELAI_AVIS_JOURS} jours pour évaluer ce séjour est dépassé."
    if deja_evalue:
        return "Vous avez déjà laissé un avis pour ce séjour."
    return None


def avis_des_reservations(reservation_ids) -> dict:
    return dict(AvisModel.objects.filter(reservation_id__in=list(reservation_ids)).values_list('reservation_id', 'id'))


def sejours_a_evaluer(user) -> list[dict]:
    today = timezone.localdate()
    sejours = reservations.sejours_termines(user.id, today - timedelta(days=DELAI_AVIS_JOURS), today)
    evalues = avis_des_reservations(s['id'] for s in sejours)
    return [s for s in sejours if s['id'] not in evalues]


def recalculer_note(hebergement_id) -> None:
    """The displayed rating and the number of reviews only come from verified reviews."""
    stats = AvisModel.objects.filter(hebergement_id=hebergement_id).aggregate(moyenne=Avg('note'), total=Count('id'))
    hebergements.mettre_a_jour_note(hebergement_id, stats['moyenne'] or 0, stats['total'])
