from django.urls import path

from .admin_views import ExperienceAdminView, ExperiencesAdminView

urlpatterns = [
    path('', ExperiencesAdminView.as_view(), name='admin-experiences'),
    path('<int:pk>/', ExperienceAdminView.as_view(), name='admin-experience'),
]
