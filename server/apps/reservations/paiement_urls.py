from django.urls import path

from .paiement_views import CompteRemboursementView, PayerView, StatutView

urlpatterns = [
    path('reservations/<uuid:pk>/payer/', PayerView.as_view(), name='paiements-payer'),
    path('reservations/<uuid:pk>/statut/', StatutView.as_view(), name='paiements-statut'),
    path('reservations/<uuid:pk>/compte-remboursement/', CompteRemboursementView.as_view(), name='paiements-compte-remboursement'),
]
