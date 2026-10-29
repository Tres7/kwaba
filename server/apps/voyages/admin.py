from django.contrib import admin

from .models import MembreModel, PropositionModel, VoyageGroupeModel


class MembreInline(admin.TabularInline):
    model = MembreModel
    extra = 0


class PropositionInline(admin.TabularInline):
    model = PropositionModel
    extra = 0


@admin.register(VoyageGroupeModel)
class VoyageGroupeAdmin(admin.ModelAdmin):
    list_display = ['nom', 'destination', 'date_debut', 'date_fin', 'organisateur_id', 'cree_le']
    search_fields = ['nom', 'destination', 'organisateur_id']
    raw_id_fields = ['proposition_retenue']
    inlines = [MembreInline, PropositionInline]
