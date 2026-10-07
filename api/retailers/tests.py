import asyncio
import threading
import time

from django.test import SimpleTestCase

from retailers.browser import exclusive_browser_session
from retailers.errors import ScraperError
from retailers.registry import RETAILER_SLUGS, get_retailer
from retailers.scrapers import checkers, picknpay, takealot, woolworths


class BrowserLockTests(SimpleTestCase):
    def test_sessions_are_serialized_across_threads_and_event_loops(self) -> None:
        active = 0
        max_active = 0
        counter_lock = threading.Lock()
        errors: list[BaseException] = []

        async def use_browser() -> None:
            nonlocal active, max_active
            async with exclusive_browser_session():
                with counter_lock:
                    active += 1
                    max_active = max(max_active, active)
                await asyncio.sleep(0.05)
                with counter_lock:
                    active -= 1

        def worker() -> None:
            try:
                asyncio.run(use_browser())
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        started = time.perf_counter()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)

        self.assertEqual(errors, [])
        self.assertEqual(max_active, 1)
        self.assertGreaterEqual(time.perf_counter() - started, 0.2)

    def test_cancelled_waiter_does_not_leak_the_lock(self) -> None:
        async def scenario() -> None:
            async with exclusive_browser_session():
                waiter = asyncio.create_task(self._enter_and_exit())
                await asyncio.sleep(0.1)
                waiter.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await waiter
            await asyncio.wait_for(self._enter_and_exit(), timeout=1)

        asyncio.run(scenario())

    async def _enter_and_exit(self) -> None:
        async with exclusive_browser_session():
            pass


class RegistryTests(SimpleTestCase):
    def test_slugs(self) -> None:
        self.assertEqual(RETAILER_SLUGS, ("takealot", "checkers", "woolworths", "picknpay"))

    def test_retailer_errors_share_a_base_class(self) -> None:
        for module, name in (
            (takealot, "TakealotScraperError"),
            (checkers, "CheckersScraperError"),
            (woolworths, "WoolworthsScraperError"),
            (picknpay, "PicknPayScraperError"),
        ):
            self.assertTrue(issubclass(getattr(module, name), ScraperError))

    def test_url_ownership(self) -> None:
        self.assertTrue(get_retailer("takealot").is_retailer_url("https://www.takealot.com/x/PLID1"))
        self.assertTrue(get_retailer("picknpay").is_retailer_url("https://www.pnp.co.za/p/1_EA"))
        self.assertFalse(get_retailer("checkers").is_retailer_url("https://www.pnp.co.za/p/1"))
        with self.assertRaises(ScraperError):
            woolworths.normalize_woolworths_url("https://evil.example/prod/_/A-1")


class ParserTests(SimpleTestCase):
    def test_takealot_search_results(self) -> None:
        html = """
        <div><a href="/acer-nitro/PLID123?x=1">Acer Nitro 5</a><span>R 15 999</span></div>
        <div><a href="/acer-nitro/PLID123">Acer Nitro 5 duplicate</a></div>
        <div><a href="/other">Not a product</a></div>
        """
        products = takealot._parse_search_results(html, max_results=5)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].url, "https://www.takealot.com/acer-nitro/PLID123")
        self.assertEqual(products[0].title, "Acer Nitro 5")
        self.assertEqual(products[0].retailer, "takealot")
        self.assertEqual(products[0].price, "R 15 999")

    def test_woolworths_reads_data_attributes(self) -> None:
        html = """
        <article data-testid="product-card" data-cnstrc-item-id="5000"
                 data-cnstrc-item-name="Full Cream Milk 2L" data-cnstrc-item-price="34.99"></article>
        """
        products = woolworths._parse_search_results(html, max_results=5)
        self.assertEqual(products[0].title, "Full Cream Milk 2L")
        self.assertEqual(products[0].price, "R34.99")
        self.assertEqual(products[0].url, "https://www.woolworths.co.za/prod/_/A-5000")

    def test_picknpay_price_ignores_text_after_add_to_cart(self) -> None:
        self.assertEqual(picknpay._extract_price("Milk R 29 .99 Add to cart R99.00"), "R29.99")

    def test_checkers_product_page_stock(self) -> None:
        html = "<h1>Bread</h1><p>R 18.99</p><button>Add to cart</button>"
        product = checkers._parse_product_page(html, "https://www.checkers.co.za/p/1EA")
        self.assertEqual(product.title, "Bread")
        self.assertEqual(product.price, "R18.99")
        self.assertTrue(product.in_stock)
