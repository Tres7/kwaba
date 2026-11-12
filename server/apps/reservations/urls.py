from django.urls import path
from .views import ReservationCalendrierView, ReservationDetailView, ReservationListCreateView

urlpatterns = [
    path('', ReservationListCreateView.as_view(), name='reservation-list'),
    path('<uuid:pk>/', ReservationDetailView.as_view(), name='reservation-detail'),
    path('<uuid:pk>/calendrier/', ReservationCalendrierView.as_view(), name='reservation-calendrier'),
]
