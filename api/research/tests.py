import json

from django.test import TestCase
from rest_framework.test import APIClient

from agents.personas import ORCHESTRATOR, RESEARCHER
from agents.run_registry import registry
from research.models import Conversation, Message


class ConversationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def create(self, **data):
        response = self.client.post("/api/conversations", data, format="json")
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_create_list_rename_reopen_delete(self):
        first = self.create()
        self.assertEqual(first["title"], "New research")
        second = self.create(title="Kettles")

        listed = self.client.get("/api/conversations").json()["conversations"]
        self.assertEqual([c["id"] for c in listed], [second["id"], first["id"]])

        response = self.client.patch(f"/api/conversations/{first['id']}", {"title": "  Air fryers  "}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Air fryers")

        conversation = Conversation.objects.get(pk=first["id"])
        Message.objects.create(conversation=conversation, role="user", content="Find an air fryer")
        Message.objects.create(conversation=conversation, role="assistant", agent=ORCHESTRATOR,
                               content="Bottom line: here you go.")
        detail = self.client.get(f"/api/conversations/{first['id']}").json()
        self.assertEqual([m["role"] for m in detail["messages"]], ["user", "assistant"])
        self.assertEqual(detail["messages"][1]["agent"], ORCHESTRATOR)

        self.assertEqual(self.client.delete(f"/api/conversations/{first['id']}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/conversations/{first['id']}").status_code, 404)
        self.assertFalse(Message.objects.filter(conversation_id=first["id"]).exists())

    def test_rename_validation(self):
        conversation = self.create()
        response = self.client.patch(f"/api/conversations/{conversation['id']}", {"title": "   "}, format="json")
        self.assertEqual(response.status_code, 422)

    def test_unknown_conversation_is_404(self):
        response = self.client.get("/api/conversations/00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, 404)

    def test_message_validation(self):
        conversation = self.create()
        url = f"/api/conversations/{conversation['id']}/messages"
        self.assertEqual(self.client.post(url, {"content": "   "}, format="json").status_code, 422)
        self.assertEqual(self.client.post(url, {"content": "x" * 4001}, format="json").status_code, 422)

    def test_delete_all_requires_confirmation(self):
        self.create()
        self.create()
        self.assertEqual(self.client.delete("/api/conversations", {}, format="json").status_code, 422)
        self.assertEqual(
            self.client.delete("/api/conversations", {"confirm": "yes"}, format="json").status_code, 422
        )
        self.assertEqual(Conversation.objects.count(), 2)
        response = self.client.delete("/api/conversations", {"confirm": "DELETE"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_running_conversation_cannot_be_deleted(self):
        conversation = self.create()
        handle = registry.start(conversation["id"])
        try:
            self.assertEqual(self.client.delete(f"/api/conversations/{conversation['id']}").status_code, 409)
            response = self.client.delete("/api/conversations", {"confirm": "DELETE"}, format="json")
            self.assertEqual(response.status_code, 409)
        finally:
            registry.finish(handle.run_id)

    def test_cancel_endpoint(self):
        conversation = self.create()
        handle = registry.start(conversation["id"])
        try:
            response = self.client.post(f"/api/runs/{handle.run_id}/cancel")
            self.assertEqual(response.json(), {"cancelled": True})
            self.assertTrue(handle.cancel_event.is_set())
        finally:
            registry.finish(handle.run_id)
        self.assertFalse(self.client.post(f"/api/runs/{handle.run_id}/cancel").json()["cancelled"])

    def test_interrupted_streaming_messages_are_closed_on_open(self):
        conversation = Conversation.objects.create()
        Message.objects.create(conversation=conversation, role="assistant", agent=RESEARCHER,
                               content="half", status=Message.Status.STREAMING)
        detail = self.client.get(f"/api/conversations/{conversation.pk}").json()
        message = detail["messages"][0]
        self.assertEqual(message["status"], "cancelled")
        self.assertEqual(message["payload"]["error"]["code"], "interrupted")

    def test_export_markdown_and_json(self):
        conversation = Conversation.objects.create(title="Kettles")
        Message.objects.create(conversation=conversation, role="user", content="Find a kettle")
        Message.objects.create(
            conversation=conversation, role="assistant", agent=RESEARCHER, content="Found one.",
            payload={"sources": [{"url": "https://shop.example.com/k", "title": "Shop",
                                  "retrieved_at": "2026-10-06T10:00:00+00:00"}]},
        )
        markdown = self.client.get(f"/api/conversations/{conversation.pk}/export?format=markdown")
        self.assertEqual(markdown.status_code, 200)
        self.assertIn("attachment", markdown["Content-Disposition"])
        text = markdown.content.decode()
        self.assertIn("# Kettles", text)
        self.assertIn("Scout", text)
        self.assertIn("https://shop.example.com/k", text)

        exported = self.client.get(f"/api/conversations/{conversation.pk}/export?format=json")
        data = json.loads(exported.content)
        self.assertEqual(data["title"], "Kettles")
        self.assertEqual(len(data["messages"]), 2)

        everything = json.loads(self.client.get("/api/conversations/export").content)
        self.assertEqual(len(everything["conversations"]), 1)

        self.assertEqual(
            self.client.get(f"/api/conversations/{conversation.pk}/export?format=pdf").status_code, 400
        )
