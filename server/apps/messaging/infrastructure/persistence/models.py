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


class MessageReportModel(models.Model):
    STATUS_CHOICES = [('pending', 'À examiner'), ('confirmed', 'Confirmé'), ('rejected', 'Rejeté')]
    REASON_CHOICES = [
        ('insult', 'Insulte'), ('hate', 'Propos haineux'), ('threat', 'Menace'), ('harassment', 'Harcèlement'),
        ('spam', 'Spam'), ('scam', 'Arnaque'), ('other', 'Autre'),
    ]

    id = models.BigAutoField(primary_key=True)
    conversation_id = models.UUIDField(db_index=True)
    message_id = models.BigIntegerField()
    reporter_id = models.UUIDField(db_index=True)
    author_id = models.UUIDField(db_index=True)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    context = models.JSONField(default=list, blank=True)
    message_created_at = models.DateTimeField()
    created_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    reviewed_by_id = models.UUIDField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    legal_hold = models.BooleanField(default=False)

    class Meta:
        app_label = 'messaging'
        db_table = 'messaging_message_report'
        constraints = [
            models.UniqueConstraint(fields=['reporter_id', 'message_id'], name='messaging_unique_report'),
        ]
        indexes = [
            models.Index(fields=['author_id', 'status'], name='messaging_report_author_idx'),
            models.Index(fields=['reporter_id', 'status', 'reviewed_at'], name='messaging_report_reporter_idx'),
        ]


class SanctionModel(models.Model):
    STEP_CHOICES = [
        ('reminder', 'Rappel des règles'), ('formal_warning', 'Avertissement formel'),
        ('short_suspension', 'Suspension courte'), ('long_suspension', 'Suspension longue'),
        ('admin_decision', 'Décision administrateur'),
    ]

    id = models.BigAutoField(primary_key=True)
    user_id = models.UUIDField(db_index=True)
    report_id = models.BigIntegerField(db_index=True)
    step = models.CharField(max_length=20, choices=STEP_CHOICES)
    category = models.CharField(max_length=20)
    created_at = models.DateTimeField(db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    contested_at = models.DateTimeField(null=True, blank=True)
    contest_text = models.TextField(blank=True)
    contest_status = models.CharField(max_length=10, blank=True)
    contest_reviewed_at = models.DateTimeField(null=True, blank=True)
    contest_reviewed_by_id = models.UUIDField(null=True, blank=True)
    contest_note = models.TextField(blank=True)

    class Meta:
        app_label = 'messaging'
        db_table = 'messaging_sanction'
        indexes = [models.Index(fields=['user_id', 'ends_at'], name='messaging_sanction_user_idx')]
