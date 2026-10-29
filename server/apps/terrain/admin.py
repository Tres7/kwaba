from django.contrib import admin

from .models import MissionModel


@admin.register(MissionModel)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type', 'statut', 'decision', 'agent_id', 'prise_le', 'terminee_le')
    list_filter = ('type', 'statut', 'decision')
    search_fields = ('titre', 'ville', 'agent__email')
    readonly_fields = [f.name for f in MissionModel._meta.fields]
