from django.urls import path

from .admin_views import GrandLivreView

urlpatterns = [
    path('grand-livre/', GrandLivreView.as_view(), name='admin-finance-grand-livre'),
]
