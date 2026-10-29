from django.contrib import admin
from django.db.models import Sum

from .models import ConversationModel, MessageModel


class MessageInline(admin.TabularInline):
    model = MessageModel
    extra = 0
    fields = ['role', 'texte', 'visible', 'tokens_entree', 'tokens_sortie', 'cree_le']
    readonly_fields = fields
    can_delete = False


@admin.register(ConversationModel)
class ConversationAdmin(admin.ModelAdmin):
    """Usage follow-up (tokens consumed); the content stays the traveller's."""
    list_display = ['titre', 'utilisateur_id', 'mis_a_jour_le', 'tokens']
    search_fields = ['titre', 'utilisateur_id']
    inlines = [MessageInline]

    @admin.display(description='Tokens (entrée / sortie)')
    def tokens(self, obj):
        t = obj.messages.aggregate(e=Sum('tokens_entree'), s=Sum('tokens_sortie'))
        return f"{t['e'] or 0} / {t['s'] or 0}"
