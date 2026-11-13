from django.contrib import admin

from .models import ActivityEntryModel


@admin.register(ActivityEntryModel)
class ActivityEntryAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'actor_email', 'target_kind', 'target_label', 'ip')
    list_filter = ('action', 'target_kind')
    search_fields = ('actor_email', 'ip', 'target_label', 'target_id')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
