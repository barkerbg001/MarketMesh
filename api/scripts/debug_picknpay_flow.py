import asyncio

from bs4 import BeautifulSoup

from app.tools.browser import run_search_flow

PNP_HOME = "https://www.pnp.co.za/"


async def main() -> None:
    html = await run_search_flow(
        PNP_HOME,
        "milk",
        ".product-grid-item",
        search_selectors='input[placeholder*="Search"]',
    )
    soup = BeautifulSoup(html, "lxml")
    print("grid items", len(soup.select(".product-grid-item")))
    print("p links", len(soup.select('a[href*="/p/"]')))
    for link in soup.select('a[href*="/p/"]')[:5]:
        print("href", link.get("href"))


if __name__ == "__main__":
    asyncio.run(main())
