from django.urls import path

from . import fraude, moderation, views

urlpatterns = [
    path('stats/', views.StatsView.as_view(), name='admin-stats'),
    # Anti-fraude
    path('anti-fraude/', fraude.AlertesView.as_view(), name='admin-anti-fraude'),
    path('anti-fraude/<int:pk>/traiter/', fraude.AlerteTraiteeView.as_view(), name='admin-anti-fraude-traiter'),
    path('anti-fraude/reports/<int:pk>/', moderation.ReportDetailView.as_view(), name='admin-report'),
    path('anti-fraude/reports/<int:pk>/confirm/', moderation.ReportConfirmView.as_view(), name='admin-report-confirm'),
    path('anti-fraude/reports/<int:pk>/reject/', moderation.ReportRejectView.as_view(), name='admin-report-reject'),
    path('anti-fraude/reports/<int:pk>/legal-hold/', moderation.ReportLegalHoldView.as_view(),
         name='admin-report-legal-hold'),
    path('anti-fraude/sanctions/<int:pk>/', moderation.SanctionDetailView.as_view(), name='admin-sanction'),
    path('anti-fraude/sanctions/<int:pk>/contest/', moderation.ContestReviewView.as_view(),
         name='admin-sanction-contest'),
    path('anti-fraude/sanctions/<int:pk>/lift/', moderation.SanctionLiftView.as_view(), name='admin-sanction-lift'),
]
