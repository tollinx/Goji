# CLAUDE.md

## Project

Goji & Gin is a RAG + MCP drink recommender: a four drink cocktail menu with a
bartender you can ask for a recommendation. The user describes a mood, the model
calls a retrieval tool over the drink corpus, and answers from what that tool
returned.

Two LLM providers are supported, selected by `LLM_PROVIDER`: Groq (default) and
Anthropic. Only the selected provider's key is required.

See README.md for setup, the request flow diagram, and deployment notes. This
file covers the parts that aren't obvious from reading the code.

## Architecture

Three pieces, deliberately separated:

- **`backend/mcp_server/`** — a standalone stdio MCP server exposing
  `search_drinks` and `get_drink` over `data/drinks.json`. It owns retrieval
  and knows nothing about the LLM or HTTP.
- **`backend/app/`** — FastAPI. `mcp_client.py` spawns the MCP server as a
  subprocess and keeps one session; `generation.py` runs the tool-calling loop
  for the configured provider; `main.py` exposes `/health` and `/ask`.
- **`frontend/src/`** — React + Vite. A menu page and an ask page.

**Why an MCP server rather than a plain Python function:** it's a real stdio
MCP server, so the same tools work from Claude Desktop or Claude Code without
this API in the loop. It also keeps generation honest — `generation.py` has no
access to the corpus and can only reach it through tool calls.

**Why two provider loops instead of one adapter:** the SDKs disagree about tool
schemas, how tool calls come back, and how results are fed in. A shared
abstraction would leak all three, so `_ask_groq` and `_ask_anthropic` each own
their loop and share only the prompt, turn cap, and drink extraction. Adding a
third provider means adding a third short function, not reworking an interface.
`mcp_client.tools` stays provider-neutral (`name`/`description`/`parameters`)
and each loop reshapes it.

**Why sentence-transformers for four documents:** semantic matching means
"something smoky and low effort" finds the suanmeitang build without sharing a
keyword with it. The cost is torch (~2GB installed). If the corpus stays this
small and install size starts to matter, TF-IDF over `search_text` would drop
the dependency entirely.

## Rules

- Retrieval always goes through `search_drinks`. Never answer a drink question
  without calling it.
- Never recommend a drink that isn't in `backend/mcp_server/data/drinks.json`.
  If nothing matches, say so — don't improvise a fifth drink or alter a recipe.
- The corpus is hand-written and offline. The serving app never rewrites it.
- Keep the MCP server a separate process. Collapsing retrieval back into an
  in-process call is what makes the tools unusable outside this app.

## Conventions

- **All styling lives in stylesheets.** SVGs in components carry geometry only
  (`viewBox`, `d`, `cx/cy/r`) — every `fill`, `stroke` and `opacity` is a class
  in CSS, so both themes are controlled from one place. Don't reintroduce
  presentation attributes or inline `style` props.
- **`theme.css` is the only file with hex colors.** Everything else uses the
  tokens. Adding a color means adding a token to both theme blocks.
- **Themes are attribute-driven.** `useTheme` resolves the OS preference and
  stamps `data-theme` on `<html>`, so `theme.css` needs one block per theme
  with no `prefers-color-scheme` copy to keep in sync. An inline script in
  `index.html` stamps it before first paint; it duplicates the storage key
  `goji-theme`, so change both together.
- **One error shape.** Every error this app raises is `{ "detail": string }`,
  rate limits included. FastAPI's built-in request validation is the exception:
  it returns `detail` as an array, which `api.ts` deliberately ignores.
- **Two files describe drinks, on purpose.** `drinks.json` is the corpus
  (recipes, retrieved). `frontend/src/data/drinks.ts` is menu display copy
  (name, one-line note, tagline). Adding a drink touches both; don't duplicate
  recipes into the frontend.

## Environment gotchas

Both of these have bitten this project before:

- **Use `backend/dev.sh`, not bare `uvicorn`.** Anaconda is on the PATH here,
  so plain `uvicorn` resolves to conda's copy and fails with
  `ModuleNotFoundError: fastapi`. `mcp_client.py` spawns the MCP server with
  `sys.executable`, so the subprocess inherits the right interpreter as long as
  the parent started from the venv.
- **Node 18+ is required** (Vite 6). `npm run dev` runs a version check first
  so the failure is legible instead of `crypto$2.getRandomValues is not a
  function`. `.nvmrc` pins 20.

## Constraints

- Dependency pins are load bearing: `mcp` requires `pydantic-settings>=2.5.2`.
  Run `pip check` after changing any pin.
- The embedding model downloads at runtime on first MCP server start, so the
  first request after a fresh install or deploy is slow.
- One MCP subprocess per uvicorn worker, each loading its own copy of the model.
- `/ask` is unauthenticated. Rate limiting and `MAX_TOKENS` cap the damage, but
  a public deploy is a public LLM key.
- Groq needs a model that supports tool calling; the app is useless without it
  since every answer must be grounded in a `search_drinks` result.
