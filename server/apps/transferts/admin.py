from django.contrib import admin, messages

from . import services
from .models import AeroportModel, ChauffeurModel, TarifTransfertModel, TransfertModel, VersementChauffeurModel


class TarifInline(admin.TabularInline):
    model = TarifTransfertModel
    extra = 0


@admin.register(AeroportModel)
class AeroportAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'ville', 'pays', 'fuseau', 'actif']
    inlines = [TarifInline]


@admin.register(ChauffeurModel)
class ChauffeurAdmin(admin.ModelAdmin):
    list_display = ['prenom', 'nom', 'telephone', 'categorie', 'vehicule', 'immatriculation', 'actif']
    list_filter = ['actif', 'categorie', 'aeroports']
    search_fields = ['prenom', 'nom', 'telephone', 'immatriculation']
    filter_horizontal = ['aeroports']


@admin.register(TransfertModel)
class TransfertAdmin(admin.ModelAdmin):
    """To assign a driver: open the transfer, choose the driver, save."""
    list_display = ['reference', 'aeroport', 'arrivee', 'numero_vol', 'categorie', 'prix', 'statut', 'chauffeur']
    list_filter = ['statut', 'aeroport', 'categorie']
    search_fields = ['numero_vol', 'voyageur__email', 'telephone']
    ordering = ['arrivee']
    readonly_fields = [
        'voyageur', 'reservation', 'aeroport', 'arrivee', 'numero_vol', 'passagers', 'bagages', 'categorie',
        'destination', 'telephone', 'message', 'prix', 'commission', 'majoration_nuit', 'moyen', 'statut',
        'expire_le', 'annule_par', 'annule_le', 'cree_le',
    ]
    exclude = ['confirmation_notifiee', 'admins_notifies', 'alerte_sans_chauffeur', 'chauffeur_notifie',
               'course_envoyee_chauffeur']
    actions = ['annuler_et_rembourser']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Only drivers of this airport with a large enough vehicle are offered
        if db_field.name == 'chauffeur':
            pk = request.resolver_match.kwargs.get('object_id')
            transfert = TransfertModel.objects.filter(pk=pk).first() if pk else None
            if transfert:
                kwargs['queryset'] = services.chauffeurs_disponibles(transfert)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if 'chauffeur' in form.changed_data and obj.chauffeur_id:
            chauffeur = obj.chauffeur
            obj.chauffeur_id = form.initial.get('chauffeur')  # the assignment goes through the service
            try:
                services.assigner_chauffeur(obj, chauffeur)
                self.message_user(request, f"{chauffeur} attribué : le voyageur va recevoir ses coordonnées.")
            except services.TransfertErreur as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
            return
        super().save_model(request, obj, form, change)

    @admin.action(description="Annuler et rembourser intégralement (aucun chauffeur disponible…)")
    def annuler_et_rembourser(self, request, queryset):
        for transfert in queryset:
            try:
                services.annuler(transfert, par='plateforme')
            except services.TransfertErreur as exc:
                self.message_user(request, f"{transfert.reference} : {exc}", level=messages.WARNING)


@admin.register(VersementChauffeurModel)
class VersementChauffeurAdmin(admin.ModelAdmin):
    list_display = ['transfert', 'chauffeur', 'montant', 'commission', 'statut', 'date_prevue', 'derniere_erreur']
    list_filter = ['statut']
