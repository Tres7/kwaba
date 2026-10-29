import uuid
from django.db import models


class FavoriModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    hebergement_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'favoris'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'hebergement_id'], name='unique_user_hebergement_favori'),
        ]

    def __str__(self):
        return f"{self.user_id} ♥ {self.hebergement_id}"
