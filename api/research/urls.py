from django.urls import path

from research.views import (
    ConversationDetailView,
    ConversationExportAllView,
    ConversationExportView,
    ConversationListView,
    ConversationMessagesView,
    RunCancelView,
)

urlpatterns = [
    path("conversations", ConversationListView.as_view(), name="conversations"),
    path("conversations/export", ConversationExportAllView.as_view(), name="conversations-export"),
    path("conversations/<uuid:conversation_id>", ConversationDetailView.as_view(), name="conversation"),
    path(
        "conversations/<uuid:conversation_id>/messages",
        ConversationMessagesView.as_view(),
        name="conversation-messages",
    ),
    path(
        "conversations/<uuid:conversation_id>/export",
        ConversationExportView.as_view(),
        name="conversation-export",
    ),
    path("runs/<str:run_id>/cancel", RunCancelView.as_view(), name="run-cancel"),
]
