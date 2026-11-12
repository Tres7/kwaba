from django.urls import path

from .views import (
    AgentsView, AppointmentIcsView, AppointmentsView, AppointmentView, AvailabilityView, CoverageView, DayLimitView,
    ExceptionsView, ExceptionView, FeedView, OnTheWayView, PublicFeedView, TargetAppointmentView,
)

urlpatterns = [
    path('availability/', AvailabilityView.as_view(), name='agenda-availability'),
    path('availability/exceptions/', ExceptionsView.as_view(), name='agenda-exceptions'),
    path('availability/exceptions/<int:pk>/', ExceptionView.as_view(), name='agenda-exception'),
    path('availability/day-limits/<str:day>/', DayLimitView.as_view(), name='agenda-day-limit'),
    path('appointments/', AppointmentsView.as_view(), name='agenda-appointments'),
    path('appointments/<uuid:pk>/', AppointmentView.as_view(), name='agenda-appointment'),
    path('appointments/for-target/<str:target_id>/', TargetAppointmentView.as_view(), name='agenda-target-appointment'),
    path('appointments/<uuid:pk>/on-the-way/', OnTheWayView.as_view(), name='agenda-on-the-way'),
    path('appointments/<uuid:pk>/ics/', AppointmentIcsView.as_view(), name='agenda-appointment-ics'),
    path('feed/', FeedView.as_view(), name='agenda-feed'),
    path('feed/<str:token>/', PublicFeedView.as_view(), name='agenda-public-feed'),
    path('admin/coverage/', CoverageView.as_view(), name='agenda-coverage'),
    path('admin/agents/', AgentsView.as_view(), name='agenda-agents'),
]
