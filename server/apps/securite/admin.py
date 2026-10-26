from django.contrib import admin

from .models import JournalAuditModel


@admin.register(JournalAuditModel)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ('cree_le', 'action', 'email', 'ip')
    list_filter = ('action',)
    search_fields = ('email', 'ip')
    date_hierarchy = 'cree_le'

    # Read-only log: nobody can change or delete it from the administration
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
