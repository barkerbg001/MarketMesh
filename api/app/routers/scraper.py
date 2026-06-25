from fastapi import APIRouter, HTTPException

from app.agents.checkers_scraper_agent import run_checkers_scraper_agent
from app.agents.picknpay_scraper_agent import run_picknpay_scraper_agent
from app.agents.scraper_agent import run_scraper_agent
from app.agents.woolworths_scraper_agent import run_woolworths_scraper_agent
from app.schemas.scraper import ScraperAgentRequest, ScraperAgentResponse
from app.services.openrouter import OpenRouterError
from app.tools.checkers_scraper import CheckersScraperError
from app.tools.picknpay_scraper import PicknPayScraperError
from app.tools.takealot_scraper import TakealotScraperError
from app.tools.woolworths_scraper import WoolworthsScraperError

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/scrape/takealot", response_model=ScraperAgentResponse)
async def scrape_takealot(request: ScraperAgentRequest) -> ScraperAgentResponse:
    try:
        return await run_scraper_agent(request.query)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TakealotScraperError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scrape failed: {exc}") from exc


@router.post("/scrape/checkers", response_model=ScraperAgentResponse)
async def scrape_checkers(request: ScraperAgentRequest) -> ScraperAgentResponse:
    try:
        return await run_checkers_scraper_agent(request.query)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except CheckersScraperError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scrape failed: {exc}") from exc


@router.post("/scrape/woolworths", response_model=ScraperAgentResponse)
async def scrape_woolworths(request: ScraperAgentRequest) -> ScraperAgentResponse:
    try:
        return await run_woolworths_scraper_agent(request.query)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except WoolworthsScraperError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scrape failed: {exc}") from exc


@router.post("/scrape/picknpay", response_model=ScraperAgentResponse)
async def scrape_picknpay(request: ScraperAgentRequest) -> ScraperAgentResponse:
    try:
        return await run_picknpay_scraper_agent(request.query)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except PicknPayScraperError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scrape failed: {exc}") from exc


@router.post("/scrape", response_model=ScraperAgentResponse, deprecated=True)
async def scrape(request: ScraperAgentRequest) -> ScraperAgentResponse:
    """Deprecated: use /scrape/takealot instead."""
    return await scrape_takealot(request)
