import asyncio
from urllib.parse import quote

from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


async def probe_url(url: str, label: str) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=USER_AGENT, locale="en-ZA")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(3000)
        print(f"\n=== {label} ===")
        print("URL:", page.url)
        print("Status:", response.status if response else None)
        inputs = await page.locator("input").evaluate_all(
            """els => els.slice(0, 15).map(e => ({
                type: e.type,
                name: e.name,
                id: e.id,
                placeholder: e.placeholder,
                visible: e.offsetParent !== null
            }))"""
        )
        print("INPUTS:", inputs)
        await browser.close()


async def main() -> None:
    await probe_url("https://www.pnp.co.za/", "PNP home")
    await probe_url("https://www.picknpay.co.za/", "picknpay.co.za")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=USER_AGENT, locale="en-ZA")
        await page.goto("https://www.pnp.co.za/", wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(3000)

        search_selectors = [
            'input[type="search"]',
            'input[placeholder*="Search"]',
            'input[name="search"]',
            "#search",
        ]
        for sel in search_selectors:
            print(f"{sel}: {await page.locator(sel).count()}")

        search = page.locator('input[placeholder*="Search"], input[type="search"]').first
        if await search.count() > 0:
            await search.fill("milk")
            await search.press("Enter")
            await page.wait_for_timeout(5000)
            print("\nAfter search URL:", page.url)
            html = await page.content()
            print("HTML length:", len(html))
            for sel in [
                'article[data-testid="product-card"]',
                '[data-testid*="product"]',
                'a[href*="/product"]',
                'a[href*="/p/"]',
                ".product-card",
                "[class*='product']",
            ]:
                print(f"  {sel}: {await page.locator(sel).count()}")

        direct = f"https://www.pnp.co.za/search?q={quote('milk')}"
        await page.goto(direct, wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(5000)
        print("\nDirect search URL:", page.url)
        for sel in [
            'article[data-testid="product-card"]',
            'a[href*="/product"]',
            "[class*='ProductCard']",
            "[class*='product-card']",
        ]:
            print(f"  {sel}: {await page.locator(sel).count()}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
