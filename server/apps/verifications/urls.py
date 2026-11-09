from django.urls import path

from .views import (
    CompteursView, DecisionView, FichierPieceView, MaPieceIdentiteView, PhotosDecisionView, PieceDecisionView, PiecesView,
    VisitesView,
)

urlpatterns = [
    path('identite/', MaPieceIdentiteView.as_view(), name='verification-identite'),
    path('identite/<uuid:user_id>/fichier/', FichierPieceView.as_view(), name='verification-identite-fichier'),
    path('identites/', PiecesView.as_view(), name='verification-identites'),
    path('identites/<uuid:user_id>/decision/', PieceDecisionView.as_view(), name='verification-identite-decision'),
    path('compteurs/', CompteursView.as_view(), name='verification-compteurs'),
    path('visites/', VisitesView.as_view(), name='verification-visites'),
    path('visites/<uuid:pk>/decision/', DecisionView.as_view(), name='verification-decision'),
    path('photos/<uuid:pk>/decision/', PhotosDecisionView.as_view(), name='verification-photos-decision'),
]
