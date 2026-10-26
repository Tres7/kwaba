from django.contrib import admin, messages

from . import services
from .models import (
    CategorieVehiculeModel, LieuRemiseModel, LocationModel, ParametresLocationModel, PartenaireLocationModel,
    VersementChauffeurLocationModel, VersementPartenaireModel,
)


@admin.register(ParametresLocationModel)
class ParametresAdmin(admin.ModelAdmin):
    """A single row: while it does not exist, rental is not offered."""
    list_display = ['__str__', 'commission_pourcent', 'delai_min_jours', 'duree_max_jours', 'annulation_gratuite_heures']

    def has_add_permission(self, request):
        return not ParametresLocationModel.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CategorieVehiculeModel)
class CategorieAdmin(admin.ModelAdmin):
    """Owners' vehicles. Without a price per day, the vehicle is not offered."""
    list_display = ['nom', 'proprietaire', 'gamme', 'places', 'prix_jour', 'caution_jours', 'caution', 'actif', 'ordre']
    list_editable = ['prix_jour', 'caution_jours', 'actif', 'ordre']
    list_filter = ['actif', 'gamme', 'boite', 'proprietaire']
    readonly_fields = ['caution']


@admin.register(LieuRemiseModel)
class LieuAdmin(admin.ModelAdmin):
    list_display = ['nom', 'ville', 'adresse_requise', 'frais', 'actif', 'ordre']
    list_editable = ['frais', 'actif', 'ordre']
    list_filter = ['actif', 'ville']


@admin.register(PartenaireLocationModel)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ['nom', 'contact', 'telephone', 'actif', 'fondateur_fin']
    list_filter = ['actif', 'lieux__ville']
    search_fields = ['nom', 'contact', 'telephone']
    filter_horizontal = ['categories', 'lieux']


@admin.register(LocationModel)
class LocationAdmin(admin.ModelAdmin):
    """To assign: open the rental, choose the owner (and the driver) and the handed-over vehicle, save."""
    list_display = ['reference', 'categorie', 'formule', 'lieu_prise', 'debut', 'jours', 'prix', 'statut', 'partenaire',
                    'chauffeur_partenaire']
    list_filter = ['statut', 'formule', 'lieu_prise__ville', 'categorie__gamme']
    search_fields = ['voyageur__email', 'telephone', 'conducteur']
    ordering = ['debut']
    readonly_fields = [
        'voyageur', 'reservation', 'categorie', 'formule', 'lieu_prise', 'adresse_prise', 'lieu_retour', 'adresse_retour',
        'debut', 'fin', 'passagers', 'telephone', 'precisions', 'conducteur', 'permis_numero', 'permis_pays', 'jours',
        'jours_hors_lome', 'jours_hors_pays', 'chauffeur_demande', 'prix_jour', 'frais_lieux', 'prix_chauffeur', 'primes',
        'prix', 'commission', 'part_kwaba_chauffeur', 'caution', 'moyen', 'statut', 'expire_le', 'annulee_par',
        'annulee_le', 'cree_le', 'chauffeur_nom', 'chauffeur_telephone',
    ]
    exclude = ['confirmation_notifiee', 'admins_notifies', 'alerte_sans_partenaire', 'partenaire_notifie',
               'location_envoyee_partenaire', 'mission_envoyee_chauffeur']
    actions = ['annuler_et_rembourser']
    CHAMPS = ('partenaire', 'chauffeur_partenaire', 'vehicule', 'immatriculation')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Only the owners who can provide this vehicle at this handover place are offered
        if db_field.name == 'partenaire':
            pk = request.resolver_match.kwargs.get('object_id')
            location = LocationModel.objects.filter(pk=pk).first() if pk else None
            if location:
                kwargs['queryset'] = services.partenaires_disponibles(location)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if set(self.CHAMPS) & set(form.changed_data):
            choix = {champ: getattr(obj, champ) for champ in self.CHAMPS}
            obj.partenaire_id = form.initial.get('partenaire')  # the assignment goes through the service
            obj.chauffeur_partenaire_id = form.initial.get('chauffeur_partenaire')
            try:
                services.attribuer(obj, partenaire=choix['partenaire'], chauffeur=choix['chauffeur_partenaire'],
                                   vehicule=choix['vehicule'], immatriculation=choix['immatriculation'])
                self.message_user(request, "Location attribuée : le voyageur va recevoir les coordonnées.")
            except services.LocationErreur as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
            return
        super().save_model(request, obj, form, change)

    @admin.action(description="Annuler et rembourser intégralement (aucun propriétaire ou chauffeur disponible…)")
    def annuler_et_rembourser(self, request, queryset):
        for location in queryset:
            try:
                services.annuler(location, par='plateforme')
            except services.LocationErreur as exc:
                self.message_user(request, f"{location.reference} : {exc}", level=messages.WARNING)


@admin.register(VersementPartenaireModel)
class VersementPartenaireAdmin(admin.ModelAdmin):
    list_display = ['location', 'partenaire', 'montant', 'commission', 'statut', 'date_prevue', 'derniere_erreur']
    list_filter = ['statut']


@admin.register(VersementChauffeurLocationModel)
class VersementChauffeurLocationAdmin(admin.ModelAdmin):
    list_display = ['location', 'chauffeur', 'montant', 'commission', 'statut', 'date_prevue', 'derniere_erreur']
    list_filter = ['statut']
