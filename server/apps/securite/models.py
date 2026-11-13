from django.db import models


class CompteurModel(models.Model):
    """Fixed-window counter (attempts, rate limits), incremented atomically by PostgreSQL.

    Django's cache (DatabaseCache) reads then writes in two queries: simultaneous requests all read
    the same value there and get around the limit. See limites.incrementer.
    """
    cle = models.CharField(max_length=200, primary_key=True)
    valeur = models.PositiveIntegerField(default=0)
    expire_le = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'securite_compteur'


class AlerteFraudeModel(models.Model):
    """Attempt to bypass the platform: contact details or off-site payment offered in a message
    or a listing. Reviewed by an administrator from the back-office (Anti-fraud)."""
    CONTEXTES = [('message', 'Message'), ('annonce', 'Annonce'), ('reservation', 'Réservation')]
    KINDS = [
        ('bypass', 'Contournement'),
        ('refusal', 'Message refusé'),
        ('simulated', 'Refus simulé'),
        ('warning_ignored', 'Envoyé après avertissement'),
        ('false_positive', 'Blocage contesté'),
        ('report', 'Signalement'),
        ('sanction', 'Sanction'),
        ('contest', 'Contestation de sanction'),
        ('abusive_reporter', 'Signaleur abusif'),
    ]

    cree_le = models.DateTimeField(auto_now_add=True, db_index=True)
    utilisateur_id = models.UUIDField(db_index=True)
    contexte = models.CharField(max_length=20, choices=CONTEXTES)
    objet_id = models.CharField(max_length=64, help_text='Conversation, annonce ou réservation concernée')
    types = models.JSONField(default=list, help_text='telephone, email, lien, reseau, application, hors_site')
    # Detected elements (the number, the address…): proof for the administrator, never shown to the other party
    extraits = models.JSONField(default=list)
    masquee = models.BooleanField(default=False, help_text='Des coordonnées ont été masquées')
    kind = models.CharField(max_length=20, choices=KINDS, default='bypass', db_index=True)
    level = models.CharField(max_length=10, blank=True)
    threat_notified_at = models.DateTimeField(null=True, blank=True)
    legal_hold = models.BooleanField(default=False)
    traitee = models.BooleanField(default=False, db_index=True)
    traitee_le = models.DateTimeField(null=True, blank=True)
    traitee_par_id = models.UUIDField(null=True, blank=True, db_index=True)
    note = models.TextField(blank=True)

    class Meta:
        db_table = 'securite_alerte_fraude'
        ordering = ['-cree_le']
        verbose_name = 'Alerte anti-fraude'
        indexes = [models.Index(fields=['utilisateur_id', '-cree_le'], name='alerte_fraude_user_idx')]

    def __str__(self):
        return f"{self.cree_le:%Y-%m-%d} {self.utilisateur_id} {', '.join(self.types)}"
