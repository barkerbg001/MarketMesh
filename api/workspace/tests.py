import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core import crypto
from core.services.openrouter import OpenRouterError
from workspace.models import WorkspaceSettings
from workspace.services import load_provider_config

KEY = "fake-openrouter-key-for-tests-only-WXYZ"


class SettingsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        crypto.reset_cache()
        self.addCleanup(crypto.reset_cache)

    def test_defaults_without_a_key_or_model(self):
        body = self.client.get("/api/settings").json()
        self.assertEqual(body["openrouter"], {"configured": False, "source": "none", "hint": None,
                                              "updated_at": None, "environment_fallback": False})
        self.assertEqual(body["default_model"], "")
        self.assertEqual(body["research_region"], "za-en")
        self.assertEqual(body["currency"], "ZAR")
        self.assertIn("us-en", [region["value"] for region in body["options"]["regions"]])

    def test_save_key_is_masked_and_encrypted(self):
        with self.assertLogs(level=logging.DEBUG) as logs:
            logging.getLogger("marketmesh.test").debug("start")
            response = self.client.put("/api/settings/openrouter-key", {"api_key": f"  {KEY} "}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(KEY, response.content.decode())
        self.assertNotIn(KEY, "\n".join(logs.output))
        status = response.json()["openrouter"]
        self.assertEqual((status["configured"], status["source"], status["hint"]), (True, "settings", "…WXYZ"))

        record = WorkspaceSettings.load()
        self.assertTrue(record.encrypted_api_key)
        self.assertNotIn(KEY, record.encrypted_api_key)
        self.assertEqual(crypto.decrypt(record.encrypted_api_key), KEY)
        self.assertEqual(load_provider_config().api_key, KEY)
        self.assertNotIn(KEY, self.client.get("/api/settings").content.decode())

    def test_remove_key(self):
        self.client.put("/api/settings/openrouter-key", {"api_key": KEY}, format="json")
        response = self.client.delete("/api/settings/openrouter-key")
        self.assertFalse(response.json()["openrouter"]["configured"])
        self.assertEqual(WorkspaceSettings.load().encrypted_api_key, "")
        self.assertIsNone(load_provider_config().api_key)

    def test_key_validation(self):
        for value in ("short", "sk-or-v1 with spaces in the middle of it", ""):
            response = self.client.put("/api/settings/openrouter-key", {"api_key": value}, format="json")
            self.assertEqual(response.status_code, 422, value)

    @override_settings(OPEN_ROUTER_API_KEY="fake-environment-key-for-tests-only")
    def test_environment_fallback_is_reported_without_revealing_it(self):
        body = self.client.get("/api/settings").content.decode()
        self.assertIn('"source":"environment"', body.replace(" ", ""))
        self.assertNotIn("from-environment", body)
        self.assertEqual(load_provider_config().key_source, "environment")

    def test_missing_encryption_key_gives_clear_error(self):
        with TemporaryDirectory() as folder, override_settings(
            ENCRYPTION_KEY=None, ENCRYPTION_KEY_AUTOCREATE=False,
            ENCRYPTION_KEY_FILE=Path(folder) / "missing.key",
        ):
            crypto.reset_cache()
            response = self.client.put("/api/settings/openrouter-key", {"api_key": KEY}, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"]["code"], "encryption_unavailable")
        self.assertNotIn(KEY, response.content.decode())

    def test_key_file_is_created_outside_the_database_when_allowed(self):
        with TemporaryDirectory() as folder, override_settings(
            ENCRYPTION_KEY=None, ENCRYPTION_KEY_AUTOCREATE=True,
            ENCRYPTION_KEY_FILE=Path(folder) / "nested" / "encryption.key",
        ):
            crypto.reset_cache()
            self.assertEqual(self.client.put("/api/settings/openrouter-key", {"api_key": KEY},
                                             format="json").status_code, 200)
            self.assertTrue((Path(folder) / "nested" / "encryption.key").exists())
            crypto.reset_cache()

    def test_update_models_and_generation_settings(self):
        response = self.client.patch("/api/settings", {
            "default_model": "vendor/model-a",
            "agent_models": {"researcher": "vendor/model-b", "analyst": ""},
            "temperature": 0.7, "max_tool_rounds": 3, "research_region": "us-en", "currency": "USD",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["agent_models"], {"researcher": "vendor/model-b"})
        self.assertEqual(body["generation"]["temperature"], 0.7)
        config = load_provider_config()
        self.assertEqual(config.model_for("researcher"), "vendor/model-b")
        self.assertEqual(config.model_for("analyst"), "vendor/model-a")
        self.assertFalse(config.retailers_enabled)

    def test_settings_validation(self):
        cases = [
            {"temperature": 3}, {"max_tokens": 10}, {"max_tool_rounds": 0}, {"request_timeout": 1000},
            {"agent_models": {"hacker": "vendor/x"}}, {"default_model": "bad model id"},
            {"research_region": "mars"}, {"currency": "BTC"},
        ]
        for payload in cases:
            response = self.client.patch("/api/settings", payload, format="json")
            self.assertEqual(response.status_code, 422, payload)

    @patch("core.services.openrouter.check_key")
    def test_connection_test_with_new_and_saved_keys(self, check_key):
        check_key.return_value = {"is_free_tier": False, "limit": None, "limit_remaining": None, "usage": 1.5}
        response = self.client.post("/api/settings/openrouter/test", {"api_key": KEY}, format="json")
        self.assertEqual(response.json()["ok"], True)
        check_key.assert_called_with(KEY)

        self.client.put("/api/settings/openrouter-key", {"api_key": KEY}, format="json")
        self.client.post("/api/settings/openrouter/test", {}, format="json")
        check_key.assert_called_with(KEY)

    @patch("core.services.openrouter.check_key")
    def test_connection_test_reports_provider_errors(self, check_key):
        check_key.side_effect = OpenRouterError("OpenRouter rejected the API key.", code="invalid_key", status=401)
        body = self.client.post("/api/settings/openrouter/test", {"api_key": KEY}, format="json").json()
        self.assertEqual(body, {"ok": False, "error": {"code": "invalid_key",
                                                       "message": "OpenRouter rejected the API key."}})
        self.assertNotIn(KEY, json.dumps(body))

    def test_connection_test_without_any_key(self):
        body = self.client.post("/api/settings/openrouter/test", {}, format="json").json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "missing_key")

    @patch("core.services.openrouter.list_models")
    def test_model_list(self, list_models):
        list_models.return_value = [{"id": "vendor/a", "name": "A", "context_length": 8000,
                                     "prompt_price": "0", "completion_price": "0", "is_free": True}]
        body = self.client.get("/api/settings/openrouter/models").json()
        self.assertEqual(body["models"][0]["id"], "vendor/a")
        list_models.side_effect = OpenRouterError("OpenRouter is unavailable.", code="provider_error", status=503)
        response = self.client.get("/api/settings/openrouter/models")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"]["code"], "provider_error")

    def test_agent_roster(self):
        body = self.client.get("/api/agents").json()
        self.assertEqual(body["avatar_style"], "notionists")
        self.assertEqual([a["name"] for a in body["agents"]], ["Mesh", "Scout", "Tally", "Atlas"])
        for agent in body["agents"]:
            self.assertTrue(agent["quirk"])
            self.assertTrue(agent["avatar_seed"])
