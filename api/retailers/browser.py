import asyncio
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from django.conf import settings
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

# Django runs each request's coroutines on its own event loop (and thread),
# so an asyncio.Lock would be bound to a single loop. A threading.Lock polled
# without blocking serializes browser sessions process-wide and stays safe to
# cancel while waiting.
_browser_lock = threading.Lock()
_LOCK_POLL_SECONDS = 0.05

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


@asynccontextmanager
async def exclusive_browser_session() -> AsyncIterator[None]:
    while not _browser_lock.acquire(blocking=False):
        await asyncio.sleep(_LOCK_POLL_SECONDS)
    try:
        yield
    finally:
        _browser_lock.release()


def _headless() -> bool:
    return bool(settings.PLAYWRIGHT_HEADLESS)


async def fetch_page_html(
    url: str,
    wait_selector: str,
    *,
    warmup_url: str | None = None,
) -> str:
    headless = _headless()
    async with exclusive_browser_session():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=headless,
                slow_mo=250 if not headless else 0,
            )
            try:
                page = await browser.new_page(user_agent=USER_AGENT, locale="en-ZA")

                if warmup_url:
                    await page.goto(warmup_url, wait_until="domcontentloaded", timeout=45_000)
                    await page.wait_for_timeout(1000)

                await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                try:
                    await page.wait_for_selector(wait_selector, timeout=15_000)
                except PlaywrightTimeoutError:
                    pass
                await page.wait_for_timeout(1500)
                if not headless:
                    await page.wait_for_timeout(2000)
                return await page.content()
            finally:
                await browser.close()


async def run_search_flow(
    home_url: str,
    query: str,
    wait_selector: str,
    *,
    search_selectors: str = (
        'input[type="search"], input[name="text"], #js-site-search-input, '
        'input[placeholder*="Search"], input[id*="autocomplete"][placeholder*="Search"]'
    ),
) -> str:
    headless = _headless()
    async with exclusive_browser_session():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=headless,
                slow_mo=250 if not headless else 0,
            )
            try:
                page = await browser.new_page(user_agent=USER_AGENT, locale="en-ZA")
                await page.goto(home_url, wait_until="domcontentloaded", timeout=45_000)
                await page.wait_for_timeout(2000)

                locator = page.locator(search_selectors)
                try:
                    await locator.first.wait_for(state="visible", timeout=15_000)
                except PlaywrightTimeoutError:
                    if await locator.count() == 0:
                        raise RuntimeError("Could not find site search input") from None

                search = locator.first
                await search.fill(query)
                await search.press("Enter")

                try:
                    await page.wait_for_selector(wait_selector, timeout=20_000)
                except PlaywrightTimeoutError:
                    pass
                await page.wait_for_timeout(2000)
                if not headless:
                    await page.wait_for_timeout(2000)
                return await page.content()
            finally:
                await browser.close()
