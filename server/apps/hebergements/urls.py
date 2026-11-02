from django.urls import path

from .alertes import AlerteConfirmationView, AlerteCreateView, AlerteDesinscriptionView
from .brouillons import BrouillonDetailView, BrouillonsView
from .lancement import InscriptionLancementView
from .views import (
    HebergementListView, HebergementDetailView, MyHebergementsView, CityListView, SuggestionsView,
    PhotoUploadView, PhotoDetailView,
    DevisView, DisponibiliteView, BlocageCreateView, BlocageDetailView, TypesLogementView, TypeLogementDetailView,
)

urlpatterns = [
    path('', HebergementListView.as_view(), name='hebergement-list'),
    path('mine/', MyHebergementsView.as_view(), name='hebergement-mine'),
    path('brouillons/', BrouillonsView.as_view(), name='hebergement-brouillons'),
    path('brouillons/<uuid:pk>/', BrouillonDetailView.as_view(), name='hebergement-brouillon'),
    path('villes/', CityListView.as_view(), name='hebergement-villes'),
    path('suggestions/', SuggestionsView.as_view(), name='hebergement-suggestions'),
    path('lancement/', InscriptionLancementView.as_view(), name='hebergement-lancement'),
    path('alertes/confirmer/', AlerteConfirmationView.as_view(), name='alerte-confirmer'),
    path('alertes/desinscrire/', AlerteDesinscriptionView.as_view(), name='alerte-desinscrire'),
    path('photos/', PhotoUploadView.as_view(), name='hebergement-photo-upload'),
    path('photos/<uuid:pk>/', PhotoDetailView.as_view(), name='hebergement-photo-detail'),
    path('blocages/<uuid:pk>/', BlocageDetailView.as_view(), name='blocage-detail'),
    path('types/<uuid:pk>/', TypeLogementDetailView.as_view(), name='type-logement-detail'),
    path('<uuid:pk>/', HebergementDetailView.as_view(), name='hebergement-detail'),
    path('<uuid:pk>/disponibilites/', DisponibiliteView.as_view(), name='hebergement-disponibilites'),
    path('<uuid:pk>/devis/', DevisView.as_view(), name='hebergement-devis'),
    path('<uuid:pk>/blocages/', BlocageCreateView.as_view(), name='hebergement-blocages'),
    path('<uuid:pk>/types/', TypesLogementView.as_view(), name='hebergement-types'),
    path('<uuid:pk>/alertes/', AlerteCreateView.as_view(), name='hebergement-alertes'),
]
