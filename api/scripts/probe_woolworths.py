import asyncio

from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-ZA",
        )
        await page.goto("https://www.woolworths.co.za/", wait_until="domcontentloaded")
        search = page.locator('input[placeholder*="Search"]').first
        await search.fill("milk")
        await search.press("Enter")
        await page.wait_for_selector("article[data-testid='product-card']", timeout=20_000)
        await page.locator("article[data-testid='product-card']").first.click()
        await page.wait_for_timeout(3000)
        print("after click", page.url)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
