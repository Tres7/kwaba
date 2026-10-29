from django.db.models import Avg, Count

from .models import AvisModel
from .services import avis_des_reservations, motif_refus

__all__ = ['avis_des_reservations', 'motif_refus', 'statistiques']


def statistiques() -> dict:
    """Reviews for the back-office dashboard: number and average rating (None without any review)."""
    stats = AvisModel.objects.aggregate(total=Count('id'), moyenne=Avg('note'))
    stats['moyenne'] = round(stats['moyenne'], 1) if stats['moyenne'] is not None else None
    return stats
