from django.urls import path

from . import admin_views

urlpatterns = [
    path('droits/', admin_views.DroitsAdminView.as_view(), name='admin-droits'),
    path('users/', admin_views.UtilisateurListView.as_view(), name='admin-users'),
    path('users/<uuid:pk>/', admin_views.UtilisateurDetailView.as_view(), name='admin-user'),
]
