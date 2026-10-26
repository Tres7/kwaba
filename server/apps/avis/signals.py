from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import AvisModel
from .services import recalculer_note


@receiver(post_delete, sender=AvisModel)
def avis_supprime(sender, instance, **kwargs):
    # E.g. booking or account deleted: the displayed rating stays faithful to the remaining reviews
    recalculer_note(instance.hebergement_id)
