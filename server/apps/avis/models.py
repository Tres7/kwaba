import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


NOTE = [MinValueValidator(1), MaxValueValidator(5)]

# Criteria rated by the traveller, in display order
CRITERES = {
    'proprete': 'Propreté',
    'conformite': 'Conforme aux photos',
    'communication': 'Communication',
    'emplacement': 'Emplacement',
    'qualite_prix': 'Rapport qualité/prix',
}


class AvisModel(models.Model):
    """Verified review: attached to a real, finished booking, only one per stay."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation_id = models.UUIDField(unique=True)
    hebergement_id = models.UUIDField(db_index=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='avis_donnes')

    note = models.PositiveSmallIntegerField(validators=NOTE)
    proprete = models.PositiveSmallIntegerField(validators=NOTE)
    conformite = models.PositiveSmallIntegerField(validators=NOTE)
    communication = models.PositiveSmallIntegerField(validators=NOTE)
    emplacement = models.PositiveSmallIntegerField(validators=NOTE)
    qualite_prix = models.PositiveSmallIntegerField(validators=NOTE)
    commentaire = models.TextField()

    reponse_hote = models.TextField(blank=True)
    reponse_le = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'avis'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(check=models.Q(note__gte=1, note__lte=5), name='avis_note_1_a_5'),
        ]

    def __str__(self):
        return f"{self.note}/5 · {self.hebergement_id} par {self.auteur_id}"
