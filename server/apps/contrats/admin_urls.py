"""Back-office routes, mounted under /api/v1/admin/contrats/."""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.ContratsAdminView.as_view(), name='contrats-admin'),
    path('parties/', views.PartiesAdminView.as_view(), name='contrats-admin-parties'),
    path('modeles/', views.ModelesAdminView.as_view(), name='contrats-admin-modeles'),
    path('modeles/<str:type_contrat>/', views.ModeleAdminView.as_view(), name='contrats-admin-modele'),
    path('<uuid:pk>/pdf/', views.ContratAdminPdfView.as_view(), name='contrats-admin-pdf'),
    path('<uuid:pk>/<str:action>/', views.ContratAdminActionView.as_view(), name='contrats-admin-action'),
]
