from fastapi import APIRouter, HTTPException

from app.agents.search_agent import run_search_agent
from app.schemas.search import SearchAgentRequest, SearchAgentResponse
from app.services.openrouter import OpenRouterError

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/search", response_model=SearchAgentResponse)
async def search(request: SearchAgentRequest) -> SearchAgentResponse:
    try:
        return await run_search_agent(request.query)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {exc}",
        ) from exc
