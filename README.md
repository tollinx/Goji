# Kurai

A multi-project document intelligence platform. Users ask questions against named
collections of indexed documents and get answers with mandatory citations. Wrong
answers are not acceptable — the system abstains when context is insufficient.

Two launch verticals:
- **Compliance** — NIST 800-53 Rev5, CMMC 2.0, FedRAMP Moderate Baseline (PDF ingestion)
- **Film** — Criterion Collection essays, director interviews (Wong Kar-wai, Tarkovsky,
  Kubrick, Bergman), Roger Ebert reviews (web scraping ingestion)

The retrieval architecture is document-agnostic. The same pipeline that handles
FedRAMP audit questions handles questions about Wong Kar-wai's cinematography.
That's the point.

## Non-negotiables (do not violate without asking first)

- Chunk by **natural document unit** — one control per chunk for compliance,
  one essay/review/interview section per chunk for film. Never fixed token windows.
- Retrieval is **hybrid**: pgvector cosine similarity + BM25 keyword search. Always both.
- Every answer **cites its sources**. No citation, no claim. Ever.
- **Abstain** when retrieved context doesn't support an answer. Never fabricate.
- Every retrieval query is **scoped by project_id**. No cross-project data leakage.
- Cross-project queries (e.g. SSP vs NIST gap analysis) use an explicit project_ids
  array — never implicit bleed between projects.
- Hard separation: ingestion/ runs **offline and once**. The serving app never re-ingests.
- Ingestion always requires a --project flag. No orphaned chunks.
- A public LLM endpoint is an open wallet: rate limiting + max_tokens cap +
  daily request ceiling are **phase 1**, not later.

## Stack

- Backend: FastAPI (Python), async, stateless
- Frontend: React + Vite → Vercel
- Database: Postgres + pgvector on **Supabase** (one instance: vectors + users + query log)
- Embeddings: BGE-large via sentence-transformers, **offline at ingestion only**
- Generation: Claude Sonnet
- Evals: Ragas + hand-built golden sets (one per project)
- Hosts: Render (backend), Vercel (frontend)

## Repo layout

```
kurai/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI: GET /projects, POST /ask (single + cross-project)
│   │   ├── retrieval.py      # hybrid search scoped by project_id
│   │   ├── generation.py     # Claude call, citation enforcement, abstention
│   │   ├── guardrails.py     # rate limiting, token caps, daily ceiling
│   │   └── db.py             # Supabase connection, projects + chunks + query_log tables
│   ├── ingestion/
│   │   ├── parse_pdf.py      # PDF → chunked JSONL (compliance)
│   │   ├── scrape_web.py     # URL → chunked JSONL (film corpus)
│   │   └── embed_and_load.py # run ONCE offline, --project flag required
│   ├── evals/
│   │   ├── nist-800-53/
│   │   │   └── golden_set.jsonl
│   │   ├── cmmc/
│   │   │   └── golden_set.jsonl
│   │   ├── film/
│   │   │   └── golden_set.jsonl
│   │   └── run_evals.py      # --project flag, writes baseline_scores/<project>.json
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ProjectSwitcher.jsx   # dropdown, updates active project
│       │   ├── QuestionChips.jsx     # example questions per project
│       │   └── CitationCard.jsx      # renders citations inline with answers
│       └── App.jsx
├── .claude/
│   ├── skills/
│   │   ├── control-chunking/         # compliance PDF chunking procedure
│   │   ├── web-chunking/             # film web content chunking procedure (NEW)
│   │   └── golden-set-authoring/     # eval triple schema + quality bar
│   ├── agents/
│   │   ├── eval-runner.md
│   │   └── retrieval-debugger.md
│   └── hooks/
│       └── post_tool_use_eval.sh
├── CLAUDE.md
└── README.md
```

## Database schema

```sql
CREATE TABLE projects (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,   -- "nist-800-53", "film"
    description TEXT,
    vertical    TEXT NOT NULL,          -- "compliance" | "film"
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chunks (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER REFERENCES projects(id),
    chunk_text  TEXT NOT NULL,
    embedding   vector(1024),           -- BGE-large dimension
    metadata    JSONB,                  -- control_id/family for compliance; director/title for film
    source_doc  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON chunks (project_id);

CREATE TABLE query_log (
    id                SERIAL PRIMARY KEY,
    project_id        INTEGER REFERENCES projects(id),
    query_text        TEXT,
    retrieved_chunk_ids INTEGER[],
    answer            TEXT,
    faithfulness_score FLOAT,
    citation_accuracy  FLOAT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
```

## /ask API shape

```json
// single project
{ "question": "What does AC-2 require?", "project_id": 1 }

// cross-project (compliance gap analysis)
{ "question": "Does our SSP satisfy AC-2?", "project_ids": [1, 3] }
```

Cross-project runs two scoped retrievals, merges results, tells Claude which
chunks came from which source, requires citations from both.

## Chunking strategy by vertical

**Compliance (PDF):** One control per chunk. control_id must appear verbatim in
chunk text (not only metadata) so BM25 can match exact ID queries like "AC-2".
Metadata: control_id, family, title, requirement_text, discussion, framework.

**Film (web):** One logical section per chunk — a complete essay, a Q&A exchange
from an interview, or a single review. Never split mid-thought. Target 300-600
tokens. Metadata: director, film_title, source (Criterion/Ebert/interview),
author, publication_date, url.

## Build order

1. **Walking skeleton, deployed** — /health + stub /ask, React frontend with
   ProjectSwitcher and example chips, rate limiting, live on Render + Vercel.
   Goal: public URL before any RAG logic exists.
2. **Golden eval sets** — 50 triples for NIST 800-53, 30 for film. Measure before build.
3. **Compliance ingestion** — parse_pdf.py + embed_and_load.py for NIST 800-53.
4. **Film ingestion** — scrape_web.py for Criterion essays + Ebert archive.
5. **Retrieval** — hybrid search, measure hit rate per project before generation.
6. **Generation** — Claude call, citations mandatory, abstention enforced.
7. **Eval harness** — Ragas per project, PostToolUse hook enforces regression checks.
8. **Instrument** — query logging from day one, /metrics endpoint.

## Working conventions

- Plan mode before any large change. Review the plan, annotate it, then build.
- Pin all dependencies in requirements.txt.
- Baseline eval scores live in evals/baseline_scores/<project-slug>.json and are
  committed to git. Regressions are visible in git diff.
- Measure retrieval hit rate before wiring generation. Fix retrieval first.