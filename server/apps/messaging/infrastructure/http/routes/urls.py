from django.urls import path
from apps.messaging.infrastructure.http.controllers.ConversationController import (
    ConversationDetailView,
    ConversationListCreateView,
    ConversationMessagesView,
    ConversationReadView,
    ConversationWithGuestView,
    UnreadCountView,
)
from apps.messaging.infrastructure.http.controllers.ModerationController import (
    DraftCheckView,
    FalsePositiveView,
    MessageReportView,
    ModerationStatusView,
    SanctionContestView,
)

urlpatterns = [
    path('unread-count/', UnreadCountView.as_view(), name='messaging-unread-count'),
    path('conversations/', ConversationListCreateView.as_view(), name='messaging-conversation-list'),
    path('conversations/avec-voyageur/', ConversationWithGuestView.as_view(), name='messaging-conversation-with-guest'),
    path('conversations/<uuid:conversation_id>/', ConversationDetailView.as_view(), name='messaging-conversation-detail'),
    path('conversations/<uuid:conversation_id>/messages/', ConversationMessagesView.as_view(), name='messaging-conversation-messages'),
    path('conversations/<uuid:conversation_id>/read/', ConversationReadView.as_view(), name='messaging-conversation-read'),
    path('conversations/<uuid:conversation_id>/false-positive/', FalsePositiveView.as_view(),
         name='messaging-false-positive'),
    path('conversations/<uuid:conversation_id>/messages/<int:message_id>/report/', MessageReportView.as_view(),
         name='messaging-message-report'),
    path('moderation/check/', DraftCheckView.as_view(), name='messaging-moderation-check'),
    path('moderation/status/', ModerationStatusView.as_view(), name='messaging-moderation-status'),
    path('moderation/sanctions/<int:sanction_id>/contest/', SanctionContestView.as_view(),
         name='messaging-sanction-contest'),
]
