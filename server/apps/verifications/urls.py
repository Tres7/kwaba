from django.urls import path

from .appointment_views import (
    BookByPhoneView, BookView, CancelView, FreeSlotsView, MoveSlotsView, MoveView, MyVisitView, ReassignView,
)
from .views import (
    CompteursView, CorrectionPositionView, DecisionView, FichierPieceView, LirePositionView, MaPieceIdentiteView,
    PhotosDecisionView, PieceDecisionView, PiecesView, PositionsView, VisitesView,
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
    path('positions/', PositionsView.as_view(), name='verification-positions'),
    path('positions/lire/', LirePositionView.as_view(), name='verification-position-lire'),
    path('positions/<uuid:pk>/', CorrectionPositionView.as_view(), name='verification-position-correction'),
    path('visit/', MyVisitView.as_view(), name='verification-my-visit'),
    path('visit/slots/', FreeSlotsView.as_view(), name='verification-visit-slots'),
    path('visit/book/', BookView.as_view(), name='verification-visit-book'),
    path('visit/appointments/<uuid:pk>/slots/', MoveSlotsView.as_view(), name='verification-visit-move-slots'),
    path('visit/appointments/<uuid:pk>/move/', MoveView.as_view(), name='verification-visit-move'),
    path('listings/<uuid:pk>/appointment/', BookByPhoneView.as_view(), name='verification-book-by-phone'),
    path('appointments/<uuid:pk>/cancel/', CancelView.as_view(), name='verification-appointment-cancel'),
    path('appointments/<uuid:pk>/reassign/', ReassignView.as_view(), name='verification-appointment-reassign'),
]
