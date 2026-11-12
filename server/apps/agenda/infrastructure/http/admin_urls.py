from django.urls import path

from .admin_views import AgendaSettingsView

urlpatterns = [
    path('settings/', AgendaSettingsView.as_view(), name='admin-agenda-settings'),
]
