from django.contrib import admin

from .models import PhotoVisiteModel, PieceIdentiteModel, VisiteModel


@admin.register(PieceIdentiteModel)
class PieceIdentiteAdmin(admin.ModelAdmin):
    """Status only: the document is viewed from the agent space (/agent), where every read is logged."""
    list_display = ('hote', 'type_piece', 'statut', 'soumise_le', 'verifiee_le', 'verifiee_par')
    list_filter = ('statut', 'type_piece')
    search_fields = ('hote__email', 'hote__last_name')
    exclude = ('fichier',)
    readonly_fields = ('hote', 'type_piece', 'type_contenu', 'soumise_le', 'verifiee_le', 'verifiee_par')


class PhotoVisiteInline(admin.TabularInline):
    model = PhotoVisiteModel
    extra = 0
    fields = ('cree_le',)
    readonly_fields = ('cree_le',)
    can_delete = False


@admin.register(VisiteModel)
class VisiteAdmin(admin.ModelAdmin):
    list_display = ('hebergement_id', 'decision', 'agent', 'cree_le')
    list_filter = ('decision',)
    search_fields = ('hebergement_id',)
    readonly_fields = ('hebergement_id', 'agent', 'decision', 'controles', 'commentaire', 'cree_le')
    inlines = [PhotoVisiteInline]

    def has_add_permission(self, request):
        return False
