# MarketMesh

Monorepo for the MarketMesh application.

## Structure

```
MarketMesh/
├── api/    # FastAPI backend
└── web/    # Vite + React + TypeScript frontend
```

## Agent roadmap

- [x] Search Agent
- [x] Scraper Agent (Takealot only)
- [ ] Product Matching Agent
- [ ] Recommendation Agent
- [ ] Master Orchestrator
- [ ] Price Tracking Agent
- [ ] Deal Detection Agent
- [ ] Review Agents

## Prerequisites

- **API:** Python 3.11+
- **Web:** Node.js 20+

## Getting started

Install dependencies from the repo root:

```bash
npm install
npm run setup:api
```

### API

```bash
cd api
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

From the repo root (with the venv active):

```bash
npm run dev:api
```

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/api/health | Health check |

### Web

```bash
npm run dev
```

Starts both the API and web dev servers. To run them individually: `npm run dev:api` or `npm run dev:web`.

## Development

`npm run dev` runs both services together. The API allows CORS from `http://localhost:5173` by default.

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:5173 | Web dev server |

Other root scripts: `npm run build`, `npm run preview`, `npm run lint`

### Troubleshooting

If `npm run dev` fails with a port conflict:

```bash
npm run stop:dev
npm run dev
```

Or manually on Windows:

```powershell
netstat -ano | findstr ":8000"
taskkill /F /PID <pid>
```

The `KeyboardInterrupt` / `CancelledError` tracebacks usually mean the dev server was stopped with Ctrl+C — not an app bug.

Optional API config via `api/.env`:

```env
OPEN_ROUTER_API_KEY=your-openrouter-api-key
OPEN_ROUTER_MODEL=openai/gpt-4o-mini
PLAYWRIGHT_HEADLESS=false
DEBUG=true
CORS_ORIGINS=["http://localhost:5173"]
```

### Search agent

`POST /api/agent/search` accepts `{ "query": "..." }` and uses OpenRouter plus web search to return an answer with sources.

### Scraper agent (Takealot only)

`POST /api/agent/scrape` accepts `{ "query": "..." }` and uses Playwright to scrape takealot.com only.

Example:

```bash
curl -X POST http://localhost:8000/api/agent/scrape \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"Find gaming laptops under R20000 on Takealot\"}"
```

After pulling scraper changes, run `npm run setup:api` once to install Playwright Chromium.
