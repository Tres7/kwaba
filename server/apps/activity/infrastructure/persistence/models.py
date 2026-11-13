from django.db import models
from django.utils import timezone


class ActivityEntryModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    action = models.CharField(max_length=64, db_index=True)
    actor_id = models.UUIDField(null=True, blank=True, db_index=True)
    actor_email = models.CharField(max_length=254, blank=True)
    actor_role = models.CharField(max_length=20, blank=True, default='', db_default='')
    ip = models.GenericIPAddressField(null=True, blank=True)
    target_kind = models.CharField(max_length=20, blank=True, default='', db_default='')
    target_id = models.CharField(max_length=64, blank=True, default='', db_default='')
    target_label = models.CharField(max_length=255, blank=True, default='', db_default='')
    details = models.JSONField(default=dict, blank=True)
    legacy = models.BooleanField(default=False, db_default=False)

    class Meta:
        db_table = 'activity_entry'
        ordering = ['-created_at', '-id']
        verbose_name = "Entrée du journal d'activité"
        verbose_name_plural = "Journal d'activité"
        indexes = [models.Index(fields=['target_kind', 'target_id'], name='activity_entry_target')]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.actor_email}"


class ActivityHoldModel(models.Model):
    target_kind = models.CharField(max_length=20)
    target_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'activity_hold'
        constraints = [
            models.UniqueConstraint(fields=['target_kind', 'target_id'], name='activity_one_hold_per_target'),
        ]
