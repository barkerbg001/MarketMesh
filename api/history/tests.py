from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase

from core.types import ScrapedProduct
from history.models import SearchRun
from history.services import record_run


class RecordRunTests(TestCase):
    def test_status_is_derived_from_http_status_and_errors(self) -> None:
        cases = [(200, {}, "success"), (200, {"checkers": "x"}, "partial"), (502, {"a": "b"}, "failed")]
        for http_status, errors, expected in cases:
            with self.subTest(http_status=http_status, errors=errors):
                run = record_run(
                    kind=SearchRun.Kind.PRODUCT_SEARCH,
                    query="q",
                    http_status=http_status,
                    duration_ms=5,
                    errors=errors,
                )
                assert run is not None
                self.assertEqual(run.status, expected)

    def test_database_errors_are_swallowed(self) -> None:
        with patch.object(SearchRun.objects, "create", side_effect=DatabaseError("locked")):
            with self.assertLogs("history.services", level="ERROR"):
                result = record_run(
                    kind=SearchRun.Kind.AGENT_SEARCH, query="q", http_status=200, duration_ms=1
                )
        self.assertIsNone(result)


class HistoryAdminTests(TestCase):
    def setUp(self) -> None:
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "pw-123456!")
        self.client.force_login(user)
        self.run = record_run(
            kind=SearchRun.Kind.PRODUCT_SEARCH,
            query="milk",
            retailers=["checkers"],
            http_status=200,
            duration_ms=12,
            products=[
                ScrapedProduct(
                    title="Milk", url="https://www.checkers.co.za/p/1EA", retailer="checkers"
                )
            ],
        )

    def test_changelist_and_detail_render(self) -> None:
        self.assertEqual(self.client.get("/admin/history/searchrun/").status_code, 200)
        self.assertEqual(self.client.get("/admin/history/searchrun/?q=milk").status_code, 200)
        detail = self.client.get(f"/admin/history/searchrun/{self.run.pk}/change/")
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "https://www.checkers.co.za/p/1EA")
        self.assertEqual(self.client.get("/admin/history/searchrunproduct/").status_code, 200)

    def test_history_is_read_only(self) -> None:
        self.assertEqual(self.client.get("/admin/history/searchrun/add/").status_code, 403)
