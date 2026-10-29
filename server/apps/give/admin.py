from django.contrib import admin, messages
from django.utils import timezone

from . import services
from .models import DonModel, OrganisationModel, ProjetModel, ReversementModel


class ProjetInline(admin.StackedInline):
    model = ProjetModel
    extra = 0
    fields = ['titre', 'cause', 'lieu', 'resume', 'description', 'objectif', 'image', 'actif']


@admin.register(OrganisationModel)
class OrganisationAdmin(admin.ModelAdmin):
    """An NGO only appears on the site once the verification date is filled in."""
    list_display = ['nom', 'cause', 'pays', 'ville', 'verifiee_le', 'actif']
    list_filter = ['cause', 'pays', 'actif']
    search_fields = ['nom', 'numero_enregistrement', 'contact_email']
    prepopulated_fields = {'slug': ['nom']}
    inlines = [ProjetInline]
    fieldsets = [
        (None, {'fields': ['nom', 'slug', 'cause', 'pays', 'ville', 'resume', 'description', 'logo', 'image', 'site_web',
                           'actif']}),
        ('Vérification (publique)', {'fields': ['numero_enregistrement', 'verifiee_le', 'verification']}),
        ('Contact et reversements (jamais affichés)', {'fields': ['contact_nom', 'contact_email', 'contact_telephone',
                                                                 'coordonnees_reversement']}),
    ]


class DonInline(admin.TabularInline):
    model = DonModel
    extra = 0
    can_delete = False
    fields = ['reference', 'paye_le', 'montant_ong', 'donateur_affiche']
    readonly_fields = fields

    @admin.display(description='Donateur')
    def donateur_affiche(self, don):
        # Identity passed on to the NGO only with the donor's consent
        if not don.partage_identite or don.donateur is None:
            return 'Anonyme'
        return f"{don.donateur.get_full_name()} <{don.donateur.email}>"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ReversementModel)
class ReversementAdmin(admin.ModelAdmin):
    """After the transfer: attach the proof, fill in the reference and switch to "Done"."""
    list_display = ['reference', 'organisation', 'periode', 'montant', 'nb_dons', 'date_prevue', 'statut', 'effectue_le']
    list_filter = ['statut', 'organisation']
    readonly_fields = ['organisation', 'periode', 'montant', 'nb_dons', 'date_prevue', 'coordonnees']
    fields = ['organisation', 'coordonnees', 'periode', 'montant', 'nb_dons', 'date_prevue', 'statut', 'moyen',
              'reference_operation', 'effectue_le', 'justificatif', 'note']
    inlines = [DonInline]

    @admin.display(description="Coordonnées de reversement de l'ONG")
    def coordonnees(self, r):
        return r.organisation.coordonnees_reversement or 'À renseigner sur la fiche de l\'ONG'

    def has_add_permission(self, request):
        return False  # created every month by the worker

    def save_model(self, request, obj, form, change):
        if obj.statut == 'effectue':
            if not (obj.justificatif and obj.reference_operation and obj.moyen):
                obj.statut = 'a_effectuer'
                self.message_user(request, "Pour passer à « Effectué », joignez la preuve et indiquez le moyen et la "
                                           "référence du virement.", level=messages.ERROR)
            elif not obj.effectue_le:
                obj.effectue_le = timezone.localdate()
        super().save_model(request, obj, form, change)


@admin.register(DonModel)
class DonAdmin(admin.ModelAdmin):
    list_display = ['reference', 'organisation', 'montant', 'total', 'montant_ong', 'statut', 'paye_le', 'reversement']
    list_filter = ['statut', 'organisation', 'couvre_frais']
    search_fields = ['donateur_id']
    readonly_fields = [f.name for f in DonModel._meta.fields]
    actions = ['preparer_reversements']

    def has_add_permission(self, request):
        return False

    @admin.action(description="Préparer maintenant les reversements des mois terminés")
    def preparer_reversements(self, request, queryset):
        n = services.preparer_reversements()
        self.message_user(request, f"{n} don(s) rattaché(s) à un reversement.")
