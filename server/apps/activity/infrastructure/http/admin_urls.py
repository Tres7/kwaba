from django.urls import path

from .admin_views import ActivityDetailView, ActivityExportView, ActivityListView

urlpatterns = [
    path('', ActivityListView.as_view(), name='admin-activity'),
    path('export/', ActivityExportView.as_view(), name='admin-activity-export'),
    path('<int:pk>/', ActivityDetailView.as_view(), name='admin-activity-detail'),
]
