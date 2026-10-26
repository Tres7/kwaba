from django.urls import path

from apps.hebergements.lancement import LancementAdminView

from . import experiences, fraude, give, locations, transferts, views

urlpatterns = [
    path('stats/', views.StatsView.as_view(), name='admin-stats'),
    path('lancement/', LancementAdminView.as_view(), name='admin-lancement'),
    path('users/', views.UtilisateurListView.as_view(), name='admin-users'),
    path('users/<uuid:pk>/', views.UtilisateurDetailView.as_view(), name='admin-user'),
    path('hebergements/', views.HebergementListView.as_view(), name='admin-hebergements'),
    path('hebergements/<uuid:pk>/', views.HebergementDetailView.as_view(), name='admin-hebergement'),
    path('reservations/', views.ReservationListView.as_view(), name='admin-reservations'),
    path('reservations/<uuid:pk>/annuler/', views.ReservationAnnulerView.as_view(), name='admin-reservation-annuler'),
    path('avis/', views.AvisListView.as_view(), name='admin-avis'),
    path('avis/<uuid:pk>/', views.AvisDetailView.as_view(), name='admin-avis-detail'),
    # Anti-fraude
    path('anti-fraude/', fraude.AlertesView.as_view(), name='admin-anti-fraude'),
    path('anti-fraude/<int:pk>/traiter/', fraude.AlerteTraiteeView.as_view(), name='admin-anti-fraude-traiter'),
    # Location de voiture
    path('location/regles/', locations.ParametresView.as_view(), name='admin-location-regles'),
    path('location/categories/', locations.CategoriesView.as_view(), name='admin-location-categories'),
    path('location/categories/<int:pk>/', locations.CategorieView.as_view(), name='admin-location-categorie'),
    path('location/categories/<int:pk>/photos/', locations.PhotosCategorieView.as_view(), name='admin-location-categorie-photos'),
    path('location/categories/<int:pk>/photos/<int:photo_id>/', locations.PhotoCategorieView.as_view(),
         name='admin-location-categorie-photo'),
    path('location/lieux/', locations.LieuxView.as_view(), name='admin-location-lieux'),
    path('location/lieux/<int:pk>/', locations.LieuView.as_view(), name='admin-location-lieu'),
    path('location/loueurs/', locations.PartenairesView.as_view(), name='admin-location-loueurs'),
    path('location/loueurs/<int:pk>/', locations.PartenaireView.as_view(), name='admin-location-loueur'),
    path('location/locations/', locations.LocationsView.as_view(), name='admin-locations'),
    path('location/locations/<uuid:pk>/loueurs/', locations.LocationPartenairesView.as_view(), name='admin-location-loueurs-dispo'),
    path('location/locations/<uuid:pk>/attribuer/', locations.LocationAttribuerView.as_view(), name='admin-location-attribuer'),
    path('location/locations/<uuid:pk>/annuler/', locations.LocationAnnulerView.as_view(), name='admin-location-annuler'),
    path('location/locations/<uuid:pk>/caution/', locations.LocationCautionView.as_view(), name='admin-location-caution'),
    # Airport transfers
    path('transferts/aeroports/', transferts.AeroportsView.as_view(), name='admin-aeroports'),
    path('transferts/aeroports/<str:pk>/', transferts.AeroportView.as_view(), name='admin-aeroport'),
    path('transferts/aeroports/<str:code>/tarifs/', transferts.TarifsView.as_view(), name='admin-aeroport-tarifs'),
    path('transferts/chauffeurs/', transferts.ChauffeursView.as_view(), name='admin-chauffeurs'),
    path('transferts/chauffeurs/<int:pk>/', transferts.ChauffeurView.as_view(), name='admin-chauffeur'),
    path('transferts/transferts/', transferts.TransfertsView.as_view(), name='admin-transferts'),
    path('transferts/transferts/<uuid:pk>/chauffeurs/', transferts.TransfertChauffeursView.as_view(), name='admin-transfert-chauffeurs'),
    path('transferts/transferts/<uuid:pk>/attribuer/', transferts.TransfertAttribuerView.as_view(), name='admin-transfert-attribuer'),
    path('transferts/transferts/<uuid:pk>/annuler/', transferts.TransfertAnnulerView.as_view(), name='admin-transfert-annuler'),
    # Kwa-Ba Give
    path('give/organisations/', give.OrganisationsView.as_view(), name='admin-give-organisations'),
    path('give/organisations/<uuid:pk>/', give.OrganisationView.as_view(), name='admin-give-organisation'),
    path('give/organisations/<uuid:pk>/projets/', give.ProjetsView.as_view(), name='admin-give-projets'),
    path('give/projets/<uuid:pk>/', give.ProjetView.as_view(), name='admin-give-projet'),
    path('give/reversements/', give.ReversementsView.as_view(), name='admin-give-reversements'),
    path('give/reversements/preparer/', give.ReversementsPreparerView.as_view(), name='admin-give-preparer'),
    path('give/reversements/<uuid:pk>/effectuer/', give.ReversementEffectuerView.as_view(), name='admin-give-effectuer'),
    path('give/dons/', give.DonsView.as_view(), name='admin-give-dons'),
    # Experiences (Discover page)
    path('experiences/', experiences.ExperiencesView.as_view(), name='admin-experiences'),
    path('experiences/<int:pk>/', experiences.ExperienceView.as_view(), name='admin-experience'),
]
