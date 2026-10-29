from django.urls import path

from .admin_views import HebergementDetailView, HebergementListView, HebergementRestaurerView
from .lancement import LancementAdminView

urlpatterns = [
    path('lancement/', LancementAdminView.as_view(), name='admin-lancement'),
    path('hebergements/', HebergementListView.as_view(), name='admin-hebergements'),
    path('hebergements/<uuid:pk>/', HebergementDetailView.as_view(), name='admin-hebergement'),
    path('hebergements/<uuid:pk>/restaurer/', HebergementRestaurerView.as_view(), name='admin-hebergement-restaurer'),
]
