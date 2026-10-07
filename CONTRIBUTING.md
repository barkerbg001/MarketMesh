# Contributing to MarketMesh

Thanks for your interest in improving MarketMesh. This guide covers how to set up the project, the checks a change must pass, and the rules that keep the agents honest and the API key safe.

Before starting on something large, please open an issue to discuss it, so you don't spend time on a change that doesn't fit the project's direction. The design rationale in [docs/decisions.md](docs/decisions.md) is a good place to check first.

## Setup

Prerequisites: Python 3.12+ and Node.js 22.12+.

```bash
npm install          # web and root dependencies
npm run setup:api    # creates api/.venv, installs Python deps and Playwright Chromium, runs migrations
npm run dev          # API on http://127.0.0.1:8000, web on http://localhost:5173
```

An OpenRouter key is only needed to try the chat by hand (add it in Settings). The automated tests run offline and never need a key.

See the [README](README.md) for configuration and [docs/architecture.md](docs/architecture.md) for how the pieces fit together.

## Making a change

1. Fork the repository and create a branch from `main` with a descriptive name, such as `fix-cart-subtotals` or `add-currency-filter`.
2. Make your change, with tests (see below).
3. Run the checks:

   ```bash
   npm test             # Django tests, then Vitest
   npm run lint         # oxlint (web)
   npm run typecheck    # tsc -b (web)
   npm run build        # production build (web)
   ```

4. If you changed models, create a migration with `npm run manage -- makemigrations` and commit it.
5. If you changed behaviour, configuration, or the API, update the README or the files in `docs/`.
6. Open a pull request that explains what changed and why, and how you tested it. Include screenshots for UI changes.

Keep pull requests focused: one fix or feature each. Write commit subjects as short imperative sentences ("Fix duplicate detection for cart items"), and use the body to explain why if it isn't obvious.

## Tests

- **API** (`api/*/tests.py`): Django `TestCase`s. External services are always mocked. Use `agents.testing.FakeLLM` to script model replies and tool calls, and `configure_provider()` to set up a fake key and model. Never make real network calls to OpenRouter, search engines, or retailers in tests.
- **Web** (`web/src/**/*.test.ts`): Vitest, for pure logic such as stream parsing, the chat event reducer, mentions, prices, and routing. Keep logic that needs testing out of components so it can be tested this way.

Bug fixes should include a test that fails without the fix.

## Project rules

Some rules are central to what MarketMesh promises its users. Changes that weaken them will not be merged.

**Never fabricate.** Products, prices, and specs must come from tool results, and the tool layer in `api/agents/tools.py` enforces this. Keep the checks in code, not just in prompts, and show sources and retrieval times in the UI.

**Never combine or convert currencies.** Store prices as decimal amount plus ISO currency, and group totals by currency.

**Keep the OpenRouter key server-side.**
- The key must never appear in API responses, URLs, browser storage, logs, prompts, stream events, or the client bundle.
- Keep it encrypted at rest with the key from `MARKETMESH_ENCRYPTION_KEY` (or the git-ignored `api/.secrets/` file).
- Tests in `api/workspace/tests.py` and `api/agents/tests.py` check this; extend them if you touch key handling.

**Treat retrieved content as untrusted.** Web pages and search results must not be able to change agent instructions, trigger cart changes, or reach private network addresses. Keep untrusted tool output wrapped, and keep the address checks in `api/agents/page_fetch.py`.

**Cart changes need explicit user intent.** Agents may only change the cart when the user clearly asks. Don't give specialists cart-write tools.

**No silent model choices.** Don't hard-code model IDs or add paid fallbacks. The user picks models in Settings from OpenRouter's live list.

**Only ship settings that do something.** Every option in the UI must have an implemented effect.

## Code style

- **Python:** follow the existing style with type hints, small service functions, and thin views. Errors returned to the client use the `{"detail": ...}` shape.
- **TypeScript/React:** strict TypeScript with no `any`. Use the shadcn/ui components in `web/src/components/ui`, Tailwind classes, and existing helpers in `web/src/lib`. Keep components accessible: label controls, support the keyboard, and announce progress.
- Match the surrounding code's naming and comment density. Comments should explain constraints or intent the code can't show, not narrate what it does.
- Don't add dependencies without a clear reason. Mention any new ones in the pull request.

## Agents and personas

Agent personas (name, handle, role, quirk, intro, avatar seed) are defined in [`api/agents/personas.py`](api/agents/personas.py); prompts are in `prompts.py` and tool access in `tools.py`. If you add or change an agent:

- Keep avatar seeds stable, so existing users see the same faces.
- Specialists must not get the `delegate` tool, which is what keeps delegation loops impossible.
- Update the roster tables in the README and `docs/`.

## Retailer scrapers

The Playwright scrapers in `api/retailers/scrapers/` break when retailer sites change. Fixes are welcome, and the scripts in `api/scripts/` help debug individual stores. Be respectful of the sites: don't add aggressive concurrency or retries, and keep to publicly visible product data.

## Reporting bugs and security issues

- **Bugs:** open an issue with steps to reproduce, what you expected, what happened, and your OS, Python, and Node versions. Never paste your OpenRouter key or `api/.env` contents.
- **Security issues** (for example, a way to leak the API key or reach internal addresses through page fetching): please don't open a public issue. Report it privately through GitHub's "Report a vulnerability" option on the repository's Security tab.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
