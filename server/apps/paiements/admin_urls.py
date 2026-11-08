from django.urls import path

from .admin_views import FinancesExportView, FinancesView, TarifsView

urlpatterns = [
    path('tarifs/', TarifsView.as_view(), name='admin-tarifs'),
    path('finances/', FinancesView.as_view(), name='admin-finances'),
    path('finances/<str:format_export>/', FinancesExportView.as_view(), name='admin-finances-export'),
]
