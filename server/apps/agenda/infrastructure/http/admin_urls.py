from django.urls import path

from .admin_views import AgendaSettingsView, AgentPlanningView

urlpatterns = [
    path('settings/', AgendaSettingsView.as_view(), name='admin-agenda-settings'),
    path('planning/', AgentPlanningView.as_view(), name='admin-agenda-planning'),
]
