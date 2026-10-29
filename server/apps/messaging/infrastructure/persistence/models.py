import uuid
from django.db import models


class ConversationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hebergement_id = models.UUIDField(db_index=True)
    guest_id = models.UUIDField(db_index=True)
    # Copy of the host when the thread was created
    host_id = models.UUIDField(db_index=True)
    # Read cursors: id of the last message read by each participant
    guest_last_read_id = models.BigIntegerField(default=0)
    host_last_read_id = models.BigIntegerField(default=0)
    created_at = models.DateTimeField()
    last_message_at = models.DateTimeField()

    class Meta:
        app_label = 'messaging'
        db_table = 'messaging_conversation'
        constraints = [
            models.UniqueConstraint(fields=['hebergement_id', 'guest_id'], name='messaging_unique_hebergement_guest'),
        ]
        indexes = [
            models.Index(fields=['guest_id', '-last_message_at'], name='messaging_conv_guest_idx'),
            models.Index(fields=['host_id', '-last_message_at'], name='messaging_conv_host_idx'),
        ]

    def __str__(self):
        return f"{self.guest_id} ↔ {self.host_id} ({self.hebergement_id})"


class MessageModel(models.Model):
    # Sequential id (and not UUID): monotonic cursor for reads and polling
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        ConversationModel,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender_id = models.UUIDField(db_index=True)
    content = models.TextField()
    # Contact details hidden when sending (anti-bypass); the original text is not kept
    masque = models.BooleanField(default=False)
    created_at = models.DateTimeField()

    class Meta:
        app_label = 'messaging'
        db_table = 'messaging_message'
        indexes = [
            models.Index(fields=['conversation', 'id'], name='messaging_msg_conv_id_idx'),
        ]


class NotificationOutboxModel(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_SKIPPED = 'skipped'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'À publier'),
        (STATUS_SENT, 'Publiée'),
        (STATUS_SKIPPED, 'Écartée'),
    ]

    id = models.BigAutoField(primary_key=True)
    event_type = models.CharField(max_length=100)
    # No foreign keys: the outbox stays readable even if the thread is deleted
    conversation_id = models.UUIDField()
    message_id = models.BigIntegerField()
    recipient_id = models.UUIDField()
    payload = models.JSONField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    skip_reason = models.CharField(max_length=200, blank=True)
    available_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'messaging'
        db_table = 'messaging_notification_outbox'
        indexes = [
            models.Index(fields=['status', 'available_at'], name='messaging_outbox_due_idx'),
            models.Index(fields=['recipient_id', 'status', 'processed_at'], name='messaging_outbox_cap_idx'),
        ]
