from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class MetaEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_root(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "MarketMesh API"})

    def test_health(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_paths_have_no_trailing_slash_redirect(self) -> None:
        self.assertEqual(self.client.get("/api/health/").status_code, 404)

    def test_wrong_method_returns_405_json(self) -> None:
        response = self.client.get("/api/products/search")
        self.assertEqual(response.status_code, 405)
        self.assertIn("detail", response.json())

    def test_openapi_schema_and_docs(self) -> None:
        schema = self.client.get("/openapi.json")
        self.assertEqual(schema.status_code, 200)
        paths = schema.json()["paths"]
        for path in (
            "/api/health",
            "/api/products/search",
            "/api/conversations",
            "/api/conversations/{conversation_id}",
            "/api/conversations/{conversation_id}/messages",
            "/api/conversations/{conversation_id}/export",
            "/api/conversations/export",
            "/api/runs/{run_id}/cancel",
            "/api/cart",
            "/api/cart/{item_id}",
            "/api/cart/import",
            "/api/cart/export",
            "/api/settings",
            "/api/settings/openrouter-key",
            "/api/settings/openrouter/test",
            "/api/settings/openrouter/models",
            "/api/agents",
        ):
            self.assertIn(path, paths)
        self.assertNotIn("/api/agent/search", paths)
        self.assertEqual(self.client.get("/docs").status_code, 200)


class CorsAndCsrfTests(TestCase):
    def test_cors_preflight_allows_vite_dev_origin(self) -> None:
        response = self.client.options(
            "/api/products/search",
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_rejects_unknown_origin(self) -> None:
        response = self.client.get("/api/health", HTTP_ORIGIN="https://evil.example")
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_api_post_does_not_require_csrf_even_with_admin_session(self) -> None:
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "pw-123456!")
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)
        response = client.post("/api/products/search", {"query": ""}, format="json")
        # Reaches validation (422) rather than failing CSRF (403).
        self.assertEqual(response.status_code, 422)

    def test_admin_requires_login(self) -> None:
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.headers["Location"])
