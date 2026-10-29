from django.urls import path

from .admin_views import (
    AeroportView, AeroportsView, ChauffeurView, ChauffeursView, TarifsView, TransfertAnnulerView,
    TransfertAttribuerView, TransfertChauffeursView, TransfertsView,
)

urlpatterns = [
    path('transferts/aeroports/', AeroportsView.as_view(), name='admin-aeroports'),
    path('transferts/aeroports/<str:pk>/', AeroportView.as_view(), name='admin-aeroport'),
    path('transferts/aeroports/<str:code>/tarifs/', TarifsView.as_view(), name='admin-aeroport-tarifs'),
    path('transferts/chauffeurs/', ChauffeursView.as_view(), name='admin-chauffeurs'),
    path('transferts/chauffeurs/<int:pk>/', ChauffeurView.as_view(), name='admin-chauffeur'),
    path('transferts/transferts/', TransfertsView.as_view(), name='admin-transferts'),
    path('transferts/transferts/<uuid:pk>/chauffeurs/', TransfertChauffeursView.as_view(), name='admin-transfert-chauffeurs'),
    path('transferts/transferts/<uuid:pk>/attribuer/', TransfertAttribuerView.as_view(), name='admin-transfert-attribuer'),
    path('transferts/transferts/<uuid:pk>/annuler/', TransfertAnnulerView.as_view(), name='admin-transfert-annuler'),
]
