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

        await page.goto("https://www.checkers.co.za/", wait_until="domcontentloaded", timeout=45_000)
        search = page.locator('input[type="search"]').first
        await search.fill("milk")
        await search.press("Enter")
        try:
            await page.wait_for_selector('a[href*="/p/"], a[href*="/product/"]', timeout=20_000)
        except Exception:
            pass
        await page.wait_for_timeout(4000)
        print("url", page.url)

        for selector in [
            'a[href*="/p/"]',
            'a[href*="/product/"]',
            "[data-product-code]",
            ".product-card",
            "article",
        ]:
            count = await page.locator(selector).count()
            print(selector, count)

        links = await page.eval_on_selector_all(
            "a",
            "els => els.filter(e => e.href.includes('/p/') || e.href.includes('/product/')).slice(0,8).map(e => e.href)",
        )
        print("product links", links)

        html = await page.content()
        print("html size", len(html))
        print("has PLID-like", "/p/" in html)
        idx = html.find("/p/")
        if idx != -1:
            print("sample", html[idx : idx + 120])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
