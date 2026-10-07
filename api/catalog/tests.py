from unittest.mock import AsyncMock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from core.types import ScrapedProduct
from history.models import SearchRun
from retailers.scrapers.checkers import CheckersScraperError
from retailers.scrapers.picknpay import PicknPayScraperError
from retailers.scrapers.takealot import TakealotScraperError
from retailers.scrapers.woolworths import WoolworthsScraperError

URL = "/api/products/search"


def product(retailer: str, index: int, price: str | None = "R10.00") -> ScrapedProduct:
    return ScrapedProduct(
        title=f"{retailer} product {index}",
        price=price,
        url=f"https://{retailer}.example/p/{index}",
        retailer=retailer,
    )


def patch_retailers(**side_effects: object) -> list:
    """Patch each retailer's search function; unspecified retailers return no products."""
    patches = []
    for slug in ("takealot", "checkers", "woolworths", "picknpay"):
        effect = side_effects.get(slug, [])
        mock = AsyncMock(side_effect=effect) if isinstance(effect, BaseException) else AsyncMock(
            return_value=effect
        )
        patches.append(patch(f"retailers.scrapers.{slug}.search_{slug}", mock))
    return patches


class ProductSearchTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def _post(self, payload: object, **retailer_effects: object):
        patches = patch_retailers(**retailer_effects)
        mocks = [p.start() for p in patches]
        self.addCleanup(lambda: [p.stop() for p in patches])
        response = self.client.post(URL, payload, format="json")
        return response, dict(zip(("takealot", "checkers", "woolworths", "picknpay"), mocks, strict=True))

    def test_merges_results_and_reports_partial_errors(self) -> None:
        response, _ = self._post(
            {"query": "  milk  ", "max_results": 8},
            takealot=[product("takealot", 1), product("takealot", 2, price=None)],
            checkers=CheckersScraperError("No Checkers products found for 'milk'"),
            woolworths=RuntimeError("boom"),
            picknpay=[product("picknpay", 1)],
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["query"], "milk")
        self.assertEqual(
            [p["title"] for p in body["products"]],
            ["takealot product 1", "takealot product 2", "picknpay product 1"],
        )
        self.assertTrue(body["retrieved_at"])
        self.assertEqual(
            body["products"][1],
            {
                "key": "takealot|https://takealot.example/p/2",
                "title": "takealot product 2",
                "price": None,
                "price_amount": None,
                "currency": None,
                "url": "https://takealot.example/p/2",
                "retailer": "takealot",
                "seller": "Takealot",
                "source": "takealot",
                "source_type": "retailer",
                "image_url": None,
                "rating": None,
                "in_stock": None,
                "specs": {},
                "retrieved_at": body["retrieved_at"],
            },
        )
        first = body["products"][0]
        self.assertEqual((first["price_amount"], first["currency"]), ("10.00", "ZAR"))
        self.assertEqual(
            body["errors"],
            {
                "checkers": "No Checkers products found for 'milk'",
                "woolworths": "woolworths search failed: boom",
            },
        )

        run = SearchRun.objects.get()
        self.assertEqual(run.kind, SearchRun.Kind.PRODUCT_SEARCH)
        self.assertEqual(run.status, SearchRun.Status.PARTIAL)
        self.assertEqual(run.query, "milk")
        self.assertEqual(run.result_count, 3)
        self.assertEqual(run.products.count(), 3)
        self.assertEqual(list(run.products.values_list("position", flat=True)), [0, 1, 2])

    def test_all_retailers_failing_returns_502_with_errors(self) -> None:
        response, _ = self._post(
            {"query": "milk"},
            takealot=TakealotScraperError("t"),
            checkers=CheckersScraperError("c"),
            woolworths=WoolworthsScraperError("w"),
            picknpay=PicknPayScraperError("p"),
        )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "message": "No products found",
                    "errors": {"takealot": "t", "checkers": "c", "woolworths": "w", "picknpay": "p"},
                }
            },
        )
        self.assertEqual(SearchRun.objects.get().status, SearchRun.Status.FAILED)

    def test_no_products_and_no_errors_is_200(self) -> None:
        response, _ = self._post({"query": "milk"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual({k: body[k] for k in ("query", "products", "errors")},
                         {"query": "milk", "products": [], "errors": {}})
        self.assertIn("retrieved_at", body)

    def test_only_requested_retailers_are_searched(self) -> None:
        response, mocks = self._post(
            {"query": "bread", "retailers": ["checkers", "checkers"], "max_results": 5},
            checkers=[product("checkers", 1)],
        )
        self.assertEqual(response.status_code, 200)
        mocks["checkers"].assert_awaited_once_with("bread", max_results=5)
        for slug in ("takealot", "woolworths", "picknpay"):
            mocks[slug].assert_not_awaited()

    def test_defaults_search_all_retailers_with_12_results(self) -> None:
        for payload in ({"query": "tea"}, {"query": "tea", "retailers": []}):
            with self.subTest(payload=payload):
                _, mocks = self._post(payload)
                for mock in mocks.values():
                    mock.assert_awaited_once_with("tea", max_results=12)

    def test_whitespace_query_returns_400(self) -> None:
        response, mocks = self._post({"query": "   "})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Search query must not be empty"})
        mocks["takealot"].assert_not_awaited()
        self.assertFalse(SearchRun.objects.exists())

    def test_validation_errors_use_422_and_fastapi_shape(self) -> None:
        cases = [
            ({}, ["body", "query"]),
            ({"query": ""}, ["body", "query"]),
            ({"query": "x" * 201}, ["body", "query"]),
            ({"query": "milk", "max_results": 0}, ["body", "max_results"]),
            ({"query": "milk", "max_results": 25}, ["body", "max_results"]),
            ({"query": "milk", "retailers": ["amazon"]}, ["body", "retailers", 0]),
            (["not", "an", "object"], ["body"]),
        ]
        for payload, loc in cases:
            with self.subTest(payload=payload):
                response = self.client.post(URL, payload, format="json")
                self.assertEqual(response.status_code, 422)
                detail = response.json()["detail"]
                self.assertIsInstance(detail, list)
                self.assertEqual(detail[0]["loc"], loc)
                self.assertTrue(detail[0]["msg"])
                self.assertTrue(detail[0]["type"])

    def test_malformed_json_returns_422(self) -> None:
        response = self.client.post(URL, "{not json", content_type="application/json")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"][0]["type"], "json_invalid")

    @patch("history.services.settings")
    def test_history_can_be_disabled(self, mock_settings) -> None:
        mock_settings.SEARCH_HISTORY_ENABLED = False
        response, _ = self._post({"query": "milk"}, takealot=[product("takealot", 1)])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SearchRun.objects.exists())
