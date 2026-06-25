import asyncio

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.core.config import settings

_browser_lock = asyncio.Lock()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


async def fetch_page_html(
    url: str,
    wait_selector: str,
    *,
    warmup_url: str | None = None,
) -> str:
    async with _browser_lock:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=settings.playwright_headless,
                slow_mo=250 if not settings.playwright_headless else 0,
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
                if not settings.playwright_headless:
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
    async with _browser_lock:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=settings.playwright_headless,
                slow_mo=250 if not settings.playwright_headless else 0,
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
                if not settings.playwright_headless:
                    await page.wait_for_timeout(2000)
                return await page.content()
            finally:
                await browser.close()
