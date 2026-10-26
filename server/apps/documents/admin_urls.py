"""Back-office routes, mounted under /api/v1/admin/documents/."""
from django.urls import path

from .views import FacturePdfView, FacturesView, SignatureRepresentantView, SocieteView

urlpatterns = [
    path('societe/', SocieteView.as_view(), name='documents-societe'),
    path('societe/signature/', SignatureRepresentantView.as_view(), name='documents-societe-signature'),
    path('factures/', FacturesView.as_view(), name='documents-factures'),
    path('factures/<uuid:pk>/pdf/', FacturePdfView.as_view(), name='documents-facture-pdf'),
]
