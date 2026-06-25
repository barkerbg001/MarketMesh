import asyncio
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.core.config import settings

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


async def main() -> None:
    url = f"https://www.pnp.co.za/search/{quote('milk')}"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=settings.playwright_headless)
        page = await browser.new_page(user_agent=USER_AGENT, locale="en-ZA")
        await page.goto("https://www.pnp.co.za/", wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(1000)
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        for wait_ms in (2000, 5000, 8000):
            await page.wait_for_timeout(wait_ms)
            count = await page.locator(".product-grid-item").count()
            print(f"after {wait_ms}ms cumulative wait, grid items: {count}")
            if count:
                break
        html = await page.content()
        soup = BeautifulSoup(html, "lxml")
        print("final grid", len(soup.select(".product-grid-item")))
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
