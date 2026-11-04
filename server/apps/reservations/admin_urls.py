from django.urls import path

from .admin_views import ReservationAnnulerView, ReservationDetailView, ReservationListView

urlpatterns = [
    path('reservations/', ReservationListView.as_view(), name='admin-reservations'),
    path('reservations/<uuid:pk>/', ReservationDetailView.as_view(), name='admin-reservation'),
    path('reservations/<uuid:pk>/annuler/', ReservationAnnulerView.as_view(), name='admin-reservation-annuler'),
]
