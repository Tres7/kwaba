import uuid

from django.db import models


class ConversationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur_id = models.UUIDField(db_index=True)
    titre = models.CharField(max_length=120, blank=True)
    # Last Gemini interaction: the API keeps the history at Google (55 days on the paid plan)
    interaction_id = models.CharField(max_length=128, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'concierge'
        ordering = ['-mis_a_jour_le']
        verbose_name = 'Conversation avec le Concierge'

    def __str__(self):
        return self.titre or str(self.id)


class MessageModel(models.Model):
    """One turn of the conversation (traveller's message, answer or tool calls of the Concierge)."""
    conversation = models.ForeignKey(ConversationModel, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=[('user', 'Voyageur'), ('assistant', 'Concierge')])
    contenu = models.JSONField(default=dict, blank=True, help_text="Détail technique : appels d'outils et leurs arguments")
    # Display: readable text and Kwa-Ba offers (cards); tool results stay invisible
    texte = models.TextField(blank=True)
    cartes = models.JSONField(default=list, blank=True)
    visible = models.BooleanField(default=True)
    tokens_entree = models.PositiveIntegerField(default=0)
    tokens_sortie = models.PositiveIntegerField(default=0)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'concierge'
        ordering = ['cree_le', 'id']
