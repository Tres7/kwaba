from django.urls import path

from .lancement import InscriptionLancementView
from .views import (
    HebergementListView, HebergementDetailView, MyHebergementsView, CityListView, SuggestionsView,
    PhotoUploadView, PhotoDetailView,
    DisponibiliteView, BlocageCreateView, BlocageDetailView, TypesLogementView, TypeLogementDetailView,
)

urlpatterns = [
    path('', HebergementListView.as_view(), name='hebergement-list'),
    path('mine/', MyHebergementsView.as_view(), name='hebergement-mine'),
    path('villes/', CityListView.as_view(), name='hebergement-villes'),
    path('suggestions/', SuggestionsView.as_view(), name='hebergement-suggestions'),
    path('lancement/', InscriptionLancementView.as_view(), name='hebergement-lancement'),
    path('photos/', PhotoUploadView.as_view(), name='hebergement-photo-upload'),
    path('photos/<uuid:pk>/', PhotoDetailView.as_view(), name='hebergement-photo-detail'),
    path('blocages/<uuid:pk>/', BlocageDetailView.as_view(), name='blocage-detail'),
    path('types/<uuid:pk>/', TypeLogementDetailView.as_view(), name='type-logement-detail'),
    path('<uuid:pk>/', HebergementDetailView.as_view(), name='hebergement-detail'),
    path('<uuid:pk>/disponibilites/', DisponibiliteView.as_view(), name='hebergement-disponibilites'),
    path('<uuid:pk>/blocages/', BlocageCreateView.as_view(), name='hebergement-blocages'),
    path('<uuid:pk>/types/', TypesLogementView.as_view(), name='hebergement-types'),
]
