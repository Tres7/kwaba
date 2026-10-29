from django.contrib import admin

from .models import ConditionsHoteModel, PaiementModel, ProfilVersementModel, RemboursementModel, VersementModel


@admin.register(PaiementModel)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ['reference', 'montant', 'statut', 'mode', 'transaction_id', 'cree_le']
    list_filter = ['statut', 'prestataire']
    search_fields = ['transaction_id', 'reservation_id', 'transfert_id', 'location_id', 'don_id']
    readonly_fields = [f.name for f in PaiementModel._meta.fields]


@admin.register(VersementModel)
class VersementAdmin(admin.ModelAdmin):
    list_display = ['reservation_id', 'hote_id', 'montant', 'commission', 'statut', 'date_prevue', 'derniere_erreur']
    list_filter = ['statut']
    search_fields = ['hote_id', 'payout_id']


@admin.register(RemboursementModel)
class RemboursementAdmin(admin.ModelAdmin):
    list_display = ['reference', 'montant', 'motif', 'statut', 'derniere_erreur', 'cree_le']
    list_filter = ['statut']
    search_fields = ['reservation_id', 'transfert_id', 'location_id', 'payout_id']


@admin.register(ProfilVersementModel)
class ProfilVersementAdmin(admin.ModelAdmin):
    list_display = ['hote_id', 'pays', 'operateur', 'numero', 'titulaire', 'mis_a_jour_le']
    list_filter = ['pays', 'operateur']


@admin.register(ConditionsHoteModel)
class ConditionsHoteAdmin(admin.ModelAdmin):
    list_display = ['hote_id', 'categorie', 'fondateur_debut', 'fondateur_fin', 'mis_a_jour_le']
    list_filter = ['categorie']
    search_fields = ['hote_id']
