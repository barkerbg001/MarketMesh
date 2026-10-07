import csv
import io
import json

from django.test import TestCase
from rest_framework.test import APIClient

from cart.models import CartItem
from research.models import Conversation


def product(url: str = "https://shop.example.com/kettle", **extra) -> dict:
    return {
        "title": "Acme Kettle", "url": url, "seller": "Example Shop", "price": "R 499.00",
        "price_amount": "499.00", "currency": "ZAR", "specs": {"Capacity": "1.7 L"},
        "retrieved_at": "2026-10-06T10:00:00+00:00", **extra,
    }


class CartApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def add(self, item: dict, **extra):
        return self.client.post("/api/cart", {"product": item, **extra}, format="json")

    def test_add_and_list(self):
        response = self.add(product(), quantity=2)
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["created"])
        self.assertEqual(body["item"]["line_total"], "998.00")
        self.assertEqual(body["item"]["source"], "shop.example.com")
        cart = self.client.get("/api/cart").json()
        self.assertEqual(cart["item_count"], 2)
        self.assertEqual(cart["subtotals"], [{"currency": "ZAR", "amount": "998.00", "item_count": 2}])

    def test_duplicates_are_reported_not_doubled(self):
        self.add(product())
        again = self.add(product(url="https://shop.example.com/kettle/"))
        self.assertEqual(again.status_code, 200)
        self.assertTrue(again.json()["duplicate"])
        self.assertEqual(CartItem.objects.get().quantity, 1)
        bumped = self.add(product(), increment=True, quantity=3)
        self.assertEqual(bumped.json()["item"]["quantity"], 4)

    def test_quantity_notes_and_removal(self):
        item_id = self.add(product()).json()["item"]["id"]
        response = self.client.patch(f"/api/cart/{item_id}", {"quantity": 5, "notes": "Check warranty"}, format="json")
        self.assertEqual(response.json()["item"]["quantity"], 5)
        self.assertEqual(response.json()["item"]["notes"], "Check warranty")
        self.assertEqual(self.client.patch(f"/api/cart/{item_id}", {"quantity": 0}, format="json").status_code, 422)
        self.assertEqual(self.client.patch(f"/api/cart/{item_id}", {"quantity": 100}, format="json").status_code, 422)
        self.assertEqual(self.client.patch(f"/api/cart/{item_id}", {}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(f"/api/cart/{item_id}").json()["items"], [])
        self.assertEqual(self.client.delete(f"/api/cart/{item_id}").status_code, 404)

    def test_currencies_are_never_combined_and_unknown_prices_are_counted(self):
        self.add(product())
        self.add(product(url="https://us.example.com/kettle", price="$39.99", price_amount="39.99", currency="USD"))
        self.add(product(url="https://x.example.com/kettle", price=None, price_amount=None, currency=None), quantity=2)
        self.add(product(url="https://y.example.com/kettle", price="5 BTC", price_amount="5", currency="BTC"))
        cart = self.client.get("/api/cart").json()
        self.assertEqual(cart["subtotals"], [
            {"currency": "USD", "amount": "39.99", "item_count": 1},
            {"currency": "ZAR", "amount": "499.00", "item_count": 1},
        ])
        self.assertEqual(cart["unknown_price_count"], 3)
        btc = next(i for i in cart["items"] if "y.example.com" in i["url"])
        self.assertIsNone(btc["currency"])
        self.assertIsNone(btc["line_total"])

    def test_rejects_non_http_links(self):
        response = self.add(product(url="javascript:alert(1)"))
        self.assertEqual(response.status_code, 422)
        response = self.add(product(image_url="file:///etc/passwd"))
        self.assertEqual(response.status_code, 422)

    def test_conversation_link_is_optional(self):
        conversation = Conversation.objects.create()
        self.add(product(), conversation_id=str(conversation.pk))
        self.assertEqual(CartItem.objects.get().conversation_id, conversation.pk)
        self.add(product(url="https://b.example.com/x"), conversation_id="00000000-0000-0000-0000-000000000000")
        self.assertIsNone(CartItem.objects.get(url="https://b.example.com/x").conversation_id)

    def test_clear_requires_confirmation(self):
        self.add(product())
        self.assertEqual(self.client.delete("/api/cart", {}, format="json").status_code, 422)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(self.client.delete("/api/cart", {"confirm": "CLEAR"}, format="json").json()["items"], [])

    def test_export_csv_and_json(self):
        self.add(product(), quantity=2)
        response = self.client.get("/api/cart/export?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertEqual(rows[0]["title"], "Acme Kettle")
        self.assertEqual(rows[0]["line_total"], "998.00")
        self.assertEqual(rows[0]["currency"], "ZAR")
        data = json.loads(self.client.get("/api/cart/export?format=json").content)
        self.assertEqual(data["subtotals"][0]["amount"], "998.00")
        self.assertEqual(self.client.get("/api/cart/export?format=xml").status_code, 400)

    def test_legacy_browser_cart_import(self):
        legacy = [
            {"title": "Milk 1L", "url": "https://www.checkers.co.za/p/milk", "retailer": "checkers",
             "price": "R19.99", "quantity": 2},
            {"title": "Milk 1L", "url": "https://www.checkers.co.za/p/milk", "retailer": "checkers",
             "price": "R19.99", "quantity": 1},
            {"title": "Mystery", "url": "https://unknown.example.com/x", "price": "12"},
        ]
        body = self.client.post("/api/cart/import", {"items": legacy}, format="json").json()
        self.assertEqual(body["imported"], 3)
        milk = CartItem.objects.get(title="Milk 1L")
        self.assertEqual((milk.quantity, milk.currency, str(milk.price_amount)), (3, "ZAR", "19.99"))
        mystery = CartItem.objects.get(title="Mystery")
        self.assertIsNone(mystery.price_amount)
        self.assertEqual(body["cart"]["unknown_price_count"], 1)
