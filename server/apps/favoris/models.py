import uuid
from django.conf import settings
from django.db import models


class FavoriModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favoris',
    )
    hebergement_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'favoris'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'hebergement_id'], name='unique_user_hebergement_favori'),
        ]

    def __str__(self):
        return f"{self.user_id} ♥ {self.hebergement_id}"
