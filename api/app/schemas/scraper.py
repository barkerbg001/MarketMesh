from pydantic import BaseModel, Field


class ScrapedProduct(BaseModel):
    title: str
    price: str | None = None
    url: str
    retailer: str
    rating: str | None = None
    in_stock: bool | None = None


# Backwards-compatible alias
TakealotProduct = ScrapedProduct


class ScraperAgentRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class ScraperAgentResponse(BaseModel):
    answer: str
    products: list[ScrapedProduct]
    actions: list[str]
