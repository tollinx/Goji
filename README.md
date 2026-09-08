# Goji & Gin

A four drink home cocktail menu with a bartender you can ask for a
recommendation. Describe a mood — smoky, floral, low proof, whatever — and the
model retrieves the best matching recipe from the corpus and tells you what to
make.

The drinks came from one Flushing shopping trip: dried goods from Kar Wor Tong,
tea from Ten Ren, texture and mixers from Jmart, and the alcohol from a liquor
store off Main St.

## How it works

```
you type a mood
      │
      ▼
POST /ask (FastAPI)
      │
      ▼
the model, handed the search_drinks / get_drink tool schemas
      │
      ├─ calls search_drinks(query) ──▶ MCP server ──▶ cosine similarity over
      │                                                the drink embeddings
      ├─ calls get_drink(id) ─────────▶ MCP server ──▶ the full recipe
      │
      ▼
the model writes the recommendation, grounded in what retrieval returned
      │
      ▼
{ answer, drink } back to the ask page
```

Retrieval lives in a standalone MCP server, not in the API. FastAPI spawns it
as a subprocess at startup and keeps one session open. The model never sees the
corpus directly — only the two tools.

Two providers are supported, chosen with `LLM_PROVIDER`: **Groq** (default,
open models like Llama) and **Anthropic** (Claude). Only the selected
provider's key is needed. `GET /health` reports which one is active.

## Requirements

- **Python 3.11+**
- **Node 18+** (20 recommended; `frontend/.nvmrc` pins it)

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env      # then add your API key, see Model setup
./dev.sh
```

Serves `http://localhost:8000` and starts the MCP server itself — there's no
second process to run. `GET /health` reports whether the MCP session connected.

> `dev.sh` runs the venv's `uvicorn` directly, so it works whether or not the
> venv is activated. Avoid bare `uvicorn`: with Anaconda on the PATH it
> resolves to conda's copy and fails with `ModuleNotFoundError: fastapi`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Serves `http://localhost:5173`: a menu page that scrolls into the ask page.

> Needs Node 18+. `npm run dev` checks this first and tells you to run
> `nvm use 20` rather than failing inside Vite with
> `crypto$2.getRandomValues is not a function`.

## Model setup

Pick a provider with `LLM_PROVIDER` in `backend/.env`. You only need a key for
the one you choose.

**Groq (default).** Get a key at
[console.groq.com/keys](https://console.groq.com/keys):

```
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
```

`GROQ_MODEL` must be a model that supports tool calling — the app depends on it
calling `search_drinks` before answering — **and one your account can actually
reach**. Model availability varies per account, so list yours rather than
guessing:

```bash
cd backend
./venv/bin/python -c "import os,groq; from dotenv import load_dotenv; load_dotenv('.env'); \
print(*sorted(m.id for m in groq.Groq(api_key=os.environ['GROQ_API_KEY']).models.list().data), sep='\n')"
```

Ignore the `whisper-*` (speech), `orpheus-*` (audio) and `prompt-guard-*`
(safety classifier) entries — they aren't chat models. `groq/compound*` ships
its own server-side tools and isn't a fit for this app's custom tool calling.

**Anthropic.** Get a key at
[console.anthropic.com](https://console.anthropic.com):

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-5
```

The account also needs credits — a valid key with an empty balance returns a
503 saying exactly that.

**Embeddings** are separate and always local: `EMBEDDING_MODEL=all-MiniLM-L6-v2`
needs no key and downloads (~80MB) the first time the MCP server starts, so the
first request after a fresh install is slower.

## Layout

```
backend/
  dev.sh                    start the API (and the MCP server with it)
  app/
    main.py                 /health, /ask, error handling
    generation.py           tool-calling loop, one per provider
    mcp_client.py           owns the MCP subprocess and session
    config.py               env-backed settings
    rate_limit.py           per-IP limiting
  mcp_server/
    server.py               the two MCP tools
    corpus.py               embeddings + cosine search
    data/drinks.json        the corpus — full recipes, single source of truth
frontend/
  src/
    api.ts                  typed client for /ask
    hooks/useTheme.ts       light/dark resolution and persistence
    styles/theme.css        design tokens, one block per theme
    styles/base.css         reset, type roles, shared line-art classes
    components/             MenuPage, AskPage, ThemeToggle (each with its CSS)
    data/drinks.ts          menu display copy only, not recipes
```

Recipes live in `drinks.json`. `drinks.ts` holds only the four names, one-line
notes and taglines the menu renders, so adding a drink means editing the JSON
plus a few lines of display copy — not two parallel recipe definitions.

## Conventions

- **All styling is in stylesheets.** The SVGs carry geometry only (`viewBox`,
  `d`, `cx/cy/r`); every stroke, fill and opacity comes from a class, so both
  themes are controlled from CSS.
- **One error shape.** Every error this app raises is `{ "detail": string }`,
  rate limits included. The exception is FastAPI's built-in request validation,
  which returns `detail` as an array of field errors; `api.ts` ignores that
  shape and falls back to a readable message.
- **Colors come from tokens.** `theme.css` is the only file with hex values.

## Deployment notes

- **`/ask` is unauthenticated.** Rate limiting is per IP and `MAX_TOKENS` caps
  spend per call, but a public deploy is still a public LLM key. Add auth
  before shipping this anywhere real.
- **The backend needs a paid instance.** `sentence-transformers` pulls in torch
  (~2GB installed) and the model loads into memory, which won't fit Render's
  free 512MB. `render.yaml` sets `plan: standard` for this reason.
- **The embedding model downloads at runtime**, not at build time, so the host
  needs writable cache space and network egress.
- **Set the provider key in the host's dashboard**, never in the repo.
  `render.yaml` marks `GROQ_API_KEY` and `ANTHROPIC_API_KEY` as `sync: false`;
  `backend/.env` is gitignored.
- **One MCP subprocess per worker.** Multiple uvicorn workers each spawn their
  own server and load their own copy of the model.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `[Errno 48] Address already in use` | An earlier run still holds port 8000. `lsof -nP -iTCP:8000 -sTCP:LISTEN`, then `kill <pid>`, or use `./dev.sh --port 8001`. |
| `ModuleNotFoundError: fastapi` | Bare `uvicorn` resolved to Anaconda's. Use `./dev.sh`. |
| `crypto$2.getRandomValues is not a function` | Node too old. `nvm use 20`. |
| `/ask` returns 503 | Missing key, no credit, or an unknown model name — the response body carries the upstream message verbatim. |
| `The model ... does not exist or you do not have access to it` | `GROQ_MODEL` isn't available on your account (this is a 404, not an auth failure — the key is fine). List what you can reach with the snippet under [Model setup](#model-setup) and set one of those. |
| `bad interpreter: .../venv/bin/python3` | The venv's symlinks broke, usually after moving or renaming the project folder. `rm -rf venv && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt`. |

## Using the MCP server on its own

It's a normal stdio MCP server, so Claude Desktop or Claude Code can use it
directly. Point an MCP config entry at `python -m mcp_server.server` with
`cwd` set to `backend/`, and ask about drinks from a regular chat.
