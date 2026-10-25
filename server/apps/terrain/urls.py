from django.urls import path

from .views import LibererView, MissionsView, MissionView, PrendreView, TableauView

urlpatterns = [
    path('tableau/', TableauView.as_view(), name='agent-tableau'),
    path('missions/', MissionsView.as_view(), name='agent-missions'),
    path('missions/<str:type_mission>/<str:cible>/', MissionView.as_view(), name='agent-mission'),
    path('missions/<str:type_mission>/<str:cible>/prendre/', PrendreView.as_view(), name='agent-mission-prendre'),
    path('missions/<str:type_mission>/<str:cible>/liberer/', LibererView.as_view(), name='agent-mission-liberer'),
]
