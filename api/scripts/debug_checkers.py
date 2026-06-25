import asyncio

from app.tools.browser import run_search_flow
from app.tools.checkers_scraper import _parse_search_results


async def main() -> None:
    html = await run_search_flow(
        "https://www.checkers.co.za/",
        "milk",
        'a[href*="/p/"], a[href*="/product/"]',
    )
    with open("scripts/checkers_search.html", "w", encoding="utf-8") as file:
        file.write(html)
    print("html size", len(html))
    print("/p/ count", html.count("/p/"))
    print("/product/ count", html.count("/product/"))
    products = _parse_search_results(html, 5)
    print("parsed", len(products))
    for product in products:
        print(product.title, product.price, product.url)


if __name__ == "__main__":
    asyncio.run(main())
