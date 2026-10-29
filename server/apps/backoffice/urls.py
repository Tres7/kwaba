from django.urls import path

from . import fraude, views

urlpatterns = [
    path('stats/', views.StatsView.as_view(), name='admin-stats'),
    path('users/', views.UtilisateurListView.as_view(), name='admin-users'),
    path('users/<uuid:pk>/', views.UtilisateurDetailView.as_view(), name='admin-user'),
    # Anti-fraude
    path('anti-fraude/', fraude.AlertesView.as_view(), name='admin-anti-fraude'),
    path('anti-fraude/<int:pk>/traiter/', fraude.AlerteTraiteeView.as_view(), name='admin-anti-fraude-traiter'),
]
