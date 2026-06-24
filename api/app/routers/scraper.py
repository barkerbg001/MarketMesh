from fastapi import APIRouter, HTTPException

from app.agents.scraper_agent import run_scraper_agent
from app.schemas.scraper import ScraperAgentRequest, ScraperAgentResponse
from app.services.openrouter import OpenRouterError
from app.tools.takealot_scraper import TakealotScraperError

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/scrape", response_model=ScraperAgentResponse)
async def scrape(request: ScraperAgentRequest) -> ScraperAgentResponse:
    try:
        return await run_scraper_agent(request.query)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TakealotScraperError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Scrape failed: {exc}",
        ) from exc
