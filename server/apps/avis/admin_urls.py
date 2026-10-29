from django.urls import path

from .admin_views import AvisDetailView, AvisListView

urlpatterns = [
    path('avis/', AvisListView.as_view(), name='admin-avis'),
    path('avis/<uuid:pk>/', AvisDetailView.as_view(), name='admin-avis-detail'),
]
