from django.contrib import admin

from .models import MembreModel, PropositionModel, VoyageGroupeModel


class MembreInline(admin.TabularInline):
    model = MembreModel
    extra = 0
    raw_id_fields = ['utilisateur']


class PropositionInline(admin.TabularInline):
    model = PropositionModel
    extra = 0
    raw_id_fields = ['propose_par']


@admin.register(VoyageGroupeModel)
class VoyageGroupeAdmin(admin.ModelAdmin):
    list_display = ['nom', 'destination', 'date_debut', 'date_fin', 'organisateur', 'cree_le']
    search_fields = ['nom', 'destination', 'organisateur__email']
    raw_id_fields = ['organisateur', 'proposition_retenue']
    inlines = [MembreInline, PropositionInline]
