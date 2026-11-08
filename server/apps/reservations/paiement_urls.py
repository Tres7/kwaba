from django.urls import path

from .paiement_views import (
    CompteRemboursementView, DemandeTiersView, PaiementTiersView, PayerView, StatutTiersView, StatutView,
)

urlpatterns = [
    path('reservations/<uuid:pk>/payer/', PayerView.as_view(), name='paiements-payer'),
    path('reservations/<uuid:pk>/statut/', StatutView.as_view(), name='paiements-statut'),
    path('reservations/<uuid:pk>/compte-remboursement/', CompteRemboursementView.as_view(), name='paiements-compte-remboursement'),
    # Payment by a third party
    path('reservations/<uuid:pk>/demande-tiers/', DemandeTiersView.as_view(), name='paiements-demande-tiers'),
    path('tiers/demandes/<uuid:demande_id>/statut/', StatutTiersView.as_view(), name='paiements-tiers-statut'),
    path('tiers/<str:jeton>/', PaiementTiersView.as_view(), name='paiements-tiers'),
]
