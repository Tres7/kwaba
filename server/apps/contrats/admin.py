from django.contrib import admin

from .models import PreinscriptionModel


@admin.register(PreinscriptionModel)
class PreinscriptionAdmin(admin.ModelAdmin):
    list_display = ('accepte_le', 'hote_id', 'version', 'langue', 'ip')
    list_filter = ('version', 'langue')
    search_fields = ('hote_id',)
    date_hierarchy = 'accepte_le'

    # Proof of acceptance: read-only, never edited nor deleted from the administration
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
