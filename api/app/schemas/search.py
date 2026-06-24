from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SearchAgentRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class SearchAgentResponse(BaseModel):
    answer: str
    sources: list[SearchResult]
    queries: list[str]
