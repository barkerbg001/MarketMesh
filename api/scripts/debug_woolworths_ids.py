import asyncio

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
        await page.goto("https://www.woolworths.co.za/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        search = page.locator('input[placeholder*="Search"]').first
        await search.fill("milk")
        await search.press("Enter")
        await page.wait_for_selector('article[data-testid="product-card"]', timeout=20_000)
        cards = page.locator('article[data-testid="product-card"]')
        for index in range(5):
            card = cards.nth(index)
            data = await card.evaluate(
                """el => {
                    const link = el.querySelector('a[href*="/prod/_/A-"]');
                    return {
                        cnstrcId: el.getAttribute('data-cnstrc-item-id'),
                        name: el.getAttribute('data-cnstrc-item-name'),
                        href: link ? link.href : null,
                        allLinks: [...el.querySelectorAll('a')].map(a => a.href).slice(0, 5)
                    };
                }"""
            )
            print(f"CARD {index + 1}:", data)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
