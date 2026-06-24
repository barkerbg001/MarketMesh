from pydantic import BaseModel, Field


class TakealotProduct(BaseModel):
    title: str
    price: str | None = None
    url: str
    rating: str | None = None
    in_stock: bool | None = None


class ScraperAgentRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class ScraperAgentResponse(BaseModel):
    answer: str
    products: list[TakealotProduct]
    actions: list[str]
