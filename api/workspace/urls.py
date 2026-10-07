from django.urls import path

from workspace.views import AgentListView, ApiKeyView, ModelListView, SettingsView, TestConnectionView

urlpatterns = [
    path("settings", SettingsView.as_view(), name="settings"),
    path("settings/openrouter-key", ApiKeyView.as_view(), name="settings-openrouter-key"),
    path("settings/openrouter/test", TestConnectionView.as_view(), name="settings-openrouter-test"),
    path("settings/openrouter/models", ModelListView.as_view(), name="settings-openrouter-models"),
    path("agents", AgentListView.as_view(), name="agents"),
]
