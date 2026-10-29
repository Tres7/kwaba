from django.urls import path

from .admin_views import (
    CategorieView, CategoriesView, LieuView, LieuxView, LocationAnnulerView, LocationAttribuerView,
    LocationCautionView, LocationPartenairesView, LocationsView, ParametresView, PartenaireView, PartenairesView,
    PhotoCategorieView, PhotosCategorieView,
)

urlpatterns = [
    path('location/regles/', ParametresView.as_view(), name='admin-location-regles'),
    path('location/categories/', CategoriesView.as_view(), name='admin-location-categories'),
    path('location/categories/<int:pk>/', CategorieView.as_view(), name='admin-location-categorie'),
    path('location/categories/<int:pk>/photos/', PhotosCategorieView.as_view(), name='admin-location-categorie-photos'),
    path('location/categories/<int:pk>/photos/<int:photo_id>/', PhotoCategorieView.as_view(),
         name='admin-location-categorie-photo'),
    path('location/lieux/', LieuxView.as_view(), name='admin-location-lieux'),
    path('location/lieux/<int:pk>/', LieuView.as_view(), name='admin-location-lieu'),
    path('location/loueurs/', PartenairesView.as_view(), name='admin-location-loueurs'),
    path('location/loueurs/<int:pk>/', PartenaireView.as_view(), name='admin-location-loueur'),
    path('location/locations/', LocationsView.as_view(), name='admin-locations'),
    path('location/locations/<uuid:pk>/loueurs/', LocationPartenairesView.as_view(), name='admin-location-loueurs-dispo'),
    path('location/locations/<uuid:pk>/attribuer/', LocationAttribuerView.as_view(), name='admin-location-attribuer'),
    path('location/locations/<uuid:pk>/annuler/', LocationAnnulerView.as_view(), name='admin-location-annuler'),
    path('location/locations/<uuid:pk>/caution/', LocationCautionView.as_view(), name='admin-location-caution'),
]
