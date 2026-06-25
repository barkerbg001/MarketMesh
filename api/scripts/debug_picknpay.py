import asyncio
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
PNP_HOME = "https://www.pnp.co.za/"


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=USER_AGENT, locale="en-ZA")
        await page.goto(PNP_HOME, wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(2000)
        search = page.locator('input[placeholder*="Search"]').first
        await search.fill("milk")
        await search.press("Enter")
        await page.wait_for_timeout(5000)
        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        pattern = re.compile(r"/p/\d+EA|/product/", re.I)
        seen = set()
        for link in soup.select('a[href*="/p/"]')[:20]:
            href = link.get("href")
            if not href:
                continue
            url = urljoin(PNP_HOME, href).split("?")[0]
            if url in seen:
                continue
            seen.add(url)
            container = link.find_parent(["article", "div", "li"])
            print("URL:", url)
            print("  link text:", link.get_text(" ", strip=True)[:80])
            if container:
                print("  container classes:", container.get("class"))
                titles = container.select("[class*='title'], [class*='name'], h2, h3, h4")
                for t in titles[:2]:
                    print("  title el:", t.get_text(" ", strip=True)[:80])
                text = container.get_text(" ", strip=True)[:120]
                print("  container text:", text)
            print()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
