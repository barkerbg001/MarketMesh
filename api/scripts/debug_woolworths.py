import asyncio
from urllib.parse import quote

from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=USER_AGENT, locale="en-ZA")

        await page.goto("https://www.woolworths.co.za/", wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(3000)

        search = page.locator('input[placeholder*="Search"]').first
        if await page.locator('input[placeholder*="Search"]').count() == 0:
            print("NO SEARCH INPUT")
        else:
            await search.fill("milk")
            await search.press("Enter")
            await page.wait_for_timeout(5000)
            print("AFTER SEARCH URL:", page.url)
            cards = await page.locator('article[data-testid="product-card"]').count()
            print("SEARCH FLOW CARDS:", cards)

            if cards:
                first = page.locator('article[data-testid="product-card"]').first
                attrs = await first.evaluate(
                    """el => ({
                        id: el.getAttribute('data-cnstrc-item-id'),
                        name: el.getAttribute('data-cnstrc-item-name'),
                        price: el.getAttribute('data-cnstrc-item-price')
                    })"""
                )
                print("FIRST PRODUCT:", attrs)

        direct_url = f"https://www.woolworths.co.za/cat/browse?searchterm={quote('milk')}"
        await page.goto(direct_url, wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(5000)
        cards = await page.locator('article[data-testid="product-card"]').count()
        print("DIRECT URL:", direct_url)
        print("DIRECT CARDS:", cards)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
