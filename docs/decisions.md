# Design decisions

Why MarketMesh is built the way it is, what it deliberately does not do, and what is still unfinished. For how the pieces fit together, see [architecture.md](architecture.md).

## Starting point

MarketMesh began as a price-comparison app: a FastAPI service (later Django) that scraped four South African retailers with Playwright, a browser-only cart in `localStorage`, a one-shot "Ask AI" web-search agent, and per-retailer scraper agents that the UI never called. The conversion kept everything with lasting value:

- **Kept:** the four Playwright retailer scrapers and their registry, the direct search endpoint (now also used by the agents as the `search_retailers` tool), the search-run audit log, the OpenRouter client (rewritten for streaming, tool calls, and per-user keys), and the DuckDuckGo search helper.
- **Migrated:** the browser cart. On first load, items in `localStorage["marketmesh-cart"]` are imported into the server cart once, then removed from the browser.
- **Removed:** the one-shot search agent and the per-retailer scraper agents (and their endpoints). The research team covers both jobs with grounding rules the old agents lacked.

## Interaction model

Three models were considered for how users and agents talk to each other.

| Model | How it works | Strengths | Weaknesses |
|---|---|---|---|
| **A. Single assistant with tools** | One agent with every tool. | Simplest, cheapest, fastest. | No specialisation, so one long prompt tries to cover research, comparison, and analysis. Weaker answers on mixed tasks, and the agent identities the product calls for would be cosmetic only. |
| **B. Open group chat** | Every agent sees every message and decides whether to speak. | Feels lively; agents can build on each other. | Several agents answer the same question, repeat each other's research, and can trigger each other in loops. Costs multiply per message and responses become slow and noisy. |
| **C. Orchestrator with specialists and mention routing** *(chosen)* | Mesh answers by default and delegates focused tasks. `@scout`, `@tally`, or `@atlas` alone routes the message straight to that specialist. | One clear responder per message, specialised prompts and tools, visible hand-offs, bounded cost. Users who know what they want can skip the orchestrator. | Delegation adds latency on complex requests, and Mesh's judgement decides how good the plan is. |

**Why C.** It keeps the benefits of specialists (separate prompts and toolsets) while avoiding group chat's failure modes. It is shown as a group conversation, with each message labelled by its speaker, but it is controlled like a pipeline:

- **Exactly one responder per user message.** A single specialist mention goes direct. No mention, several mentions, or `@mesh` goes to Mesh, which is told who was mentioned and delegates to them.
- **No loops.** Only Mesh has the `delegate` tool. Specialists cannot delegate, so nesting depth is one.
- **Bounded work.** `max_delegations` per turn (default 3) and `max_tool_rounds` per agent (default 5) are enforced in code, not just in prompts.
- **No duplicate research.** Identical delegations (same agent, same task) within a turn are rejected. Products already recorded in the conversation are passed to every agent as context with stable keys, and agents are told to reuse them.
- **Shared context.** Every agent receives recent history (12 messages), the products and sources recorded so far, and, when relevant, the cart.
- **Cart changes are gated.** Only Mesh can change the cart, and only when the user's message clearly asks for it ("add … to my cart", "remove … from the shortlist"). Such messages are always routed to Mesh. Specialists never get write access.

## Grounding and anti-fabrication

The tool layer enforces the rules prompts alone cannot guarantee:

- `record_product` only accepts a page the agent opened with `fetch_page` in the same turn. Most of the product name must appear on that page, and the price amount must appear too. A price is rejected if the page does not show its currency, and spec values not found on the page are dropped. Products from the retailer search tool come straight from the scrapers.
- Prices are stored as decimal amount plus ISO currency and are never converted. Cart subtotals are grouped per currency.
- After an agent finishes, links in its text that did not come from a tool result are removed.
- Comparisons must reference recorded products by key. Missing values are shown as "Unknown", and derived rows are labelled.
- Every product and source carries its retrieval time, shown in the UI.
- Prompts require estimates to be labelled as estimates and sources to be cited.

## Security model

**The OpenRouter key never reaches the browser.**
- The browser sends the key once (`PUT /api/settings/openrouter-key`). It is encrypted with Fernet before it touches the database.
- Responses only include `configured`, `source`, the last four characters, and an update time. All OpenRouter calls happen server-side.
- The key is not put in URLs or browser storage, is not logged, and is not echoed into prompts or stream events. Tests assert this for prompts, events, and logs.

**The encryption key lives outside the database.**
- It comes from `MARKETMESH_ENCRYPTION_KEY`, or in development a generated file at `api/.secrets/encryption.key` (git-ignored, along with `*.key`, `.env`, and `*.sqlite3`). Production refuses to auto-create it unless explicitly allowed.
- Copying the database alone does not reveal the key, and losing the encryption key only means re-entering the OpenRouter key.

**Retrieved content is untrusted.**
- Search snippets and fetched pages are wrapped with a note marking them as untrusted data, and the system prompt tells agents never to follow instructions found in tool results or reveal configuration.
- Tool arguments are validated in code regardless of what the model asks for.
- Page fetching only allows public http(s) hosts. It blocks loopback, private, link-local, and reserved addresses (including after redirects) to prevent server-side request forgery, and caps page size.

**Rendering.**
- Agent Markdown is rendered without raw HTML, links open in a new tab with `rel="noopener noreferrer"`, and Markdown images are rendered as their alt text so the model cannot make the browser load arbitrary URLs.
- Product images come only from http(s) URLs recorded from fetched pages.

**No silent paid fallback.**
- There is no hard-coded model. If no default model is chosen, the chat refuses to run and says why.
- The model list comes live from OpenRouter's `/models` endpoint filtered to tool-capable models, with prices shown.

**Single-user limitation.** There are no user accounts, sessions, or permissions on `/api/*`. Settings, the key, the cart, and history belong to whoever can reach the API. This keeps a local research tool simple, but it means **the API must not be exposed publicly without an authentication layer** (for example a reverse proxy with SSO or basic auth). Adding real multi-user support would mean user-scoped models for conversations, cart, and settings, plus per-user key encryption.

## Streaming transport

Chat uses a single `POST` that returns newline-delimited JSON (`application/x-ndjson`) rather than Server-Sent Events or WebSockets.

- `EventSource` cannot send a POST body, and WebSockets would need Django Channels and an ASGI server for a single-user tool.
- NDJSON over a normal streaming response works with `runserver`, Gunicorn, and the Vite proxy unchanged, and is trivial to parse incrementally (`src/lib/stream.ts`).
- The turn runs in a background thread that feeds a queue, so the HTTP response can send heartbeats and the run can be cancelled independently (`POST /api/runs/{id}/cancel`).
- The cost is that runs live in process memory, so the API must be a single process.

## Persistence choices

- **Server-side:** conversations, messages (including products, sources, comparisons, and activity in a JSON payload), the cart, and settings, all in SQLite. Research survives browser changes and can be exported.
- **Browser-side:** only appearance preferences (theme, accent, text size, density), because they must apply before the first paint and have no server meaning.
- Preferences that affect agent behaviour (region, currency, models, limits) are stored on the server.

## Avatars and attribution

Agent avatars are generated in the browser with [DiceBear](https://www.dicebear.com) from fixed seeds defined in `personas.py`, so each agent looks the same everywhere and no image is fetched from a third-party service.

| Package | Version | Licence |
|---|---|---|
| `@dicebear/core` | 9.4.x | MIT, © Florian Körner |
| `@dicebear/notionists` (code) | 9.4.x | MIT, © Florian Körner |
| Notionists artwork | – | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), designed by [Zoish](https://bio.link/heyzoish), source: [Notionists](https://heyzoish.gumroad.com/l/notionists) |

Licences were checked against the `LICENSE` files shipped in the installed packages. CC0 requires no attribution, but credit is given here and in the app's Agents settings section.

## Limitations and unfinished work

**Known limitations**
- **Single user, single process** (see above). Running turns are tracked in memory, and a turn interrupted by a restart is marked as cancelled when its conversation is reopened.
- **Retailer scraping is fragile and slow.** Sites change markup and may block automation; a four-store search can take one to two minutes and searches are serialised. Check each retailer's terms of use before relying on scraping.
- **Web search** uses DuckDuckGo through the `ddgs` library, which has no SLA and may rate-limit.
- **Currency detection** for the "page shows this currency" check is heuristic. For rand it accepts an `R` price marker, which can match unrelated text.
- **Model dependence.** Agents need tool calling. Small free models follow multi-step instructions less reliably, and answers can still be wrong.
- **No currency conversion, price history, or alerts.**
- **Bundle size.** The production JavaScript bundle is about 1 MB (335 KB gzipped), mainly Markdown rendering and avatar artwork. It is not code-split yet.

**Not yet built**
- Authentication and multi-user support.
- Price tracking over time and deal alerts.
- Cross-retailer product matching (recognising the same product at different stores).
- Review and sentiment analysis.
- Searching inside past conversations.
- End-to-end browser tests in CI; current automated tests are the Django suite (agents, chat streaming, cart, settings, exports, all with mocked external services) and Vitest unit tests for the web app's pure logic.
- Deployment configuration (Dockerfile, CI workflows).

**Verification status**
- Automated tests mock OpenRouter, web search, page fetching, and the scrapers, so they run offline.
- Manually verified in a browser against the live OpenRouter API: model listing, key testing (an invalid key is reported as rejected), and a chat turn that surfaces the provider's invalid-key error.
- **A full research turn with a valid OpenRouter key has not been verified yet**, because no valid key was available during development.
