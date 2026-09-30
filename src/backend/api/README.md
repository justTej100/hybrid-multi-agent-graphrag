# `api/` — Backend structure

FastAPI backend for Argus. Run it from `src/backend`:

```bash
uvicorn api.main:app --reload --port 8000
```

`main.py` only wires things together. Routes live in `routers/`. Shared services (database, storage, mail, ingestion, the study pipeline) live next to `api/`, not inside it.

```text
src/backend/
├── config.py                 # env loading, model helpers, kg_enabled()
├── citations.py              # [pN] parsing and link generation
├── jobs.py                   # PDF ingestion (extract, chunk, embed, optional graph)
├── storage.py                # local uploaded_pdfs/ or Supabase via db.storage.PDFStorage
├── mail/gmail.py             # flashcard email
├── agents/                   # LangGraph study pipeline (see agents/README.md)
├── db/                       # Postgres, pgvector, Neo4j adapters (see db/README.md)
└── api/
    ├── main.py               # app, lifespan, middleware, SPA
    ├── schemas.py            # shared Pydantic models
    └── routers/
        ├── auth.py           # session cookie, Google OAuth, /me, /logout
        ├── documents.py      # upload, list, status, delete, file, flashcards-open
        ├── chat.py           # /chat and /search
        ├── flashcards.py     # email, offers, subscribe, broadcast
        ├── admin.py          # config, stats, chunk inspection
        └── rate_limit.py     # guest cooldown and daily cap
```

## `main.py`

- Loads settings through `config.py` (repo-root `.env`)
- On startup calls `db.client.init_schema()`
- Mounts the routers
- Serves the React build from `src/frontend/dist` for `/`, `/login`, `/study`, and `/admin`
- `GET /health`

When `DATABASE_URL` is unset, documents, chunks, subscriptions, and chat usage stay in memory. When it is set, those calls go to Postgres. Ingestion also writes embeddings. Neo4j extraction runs only when `kg_enabled()` is true (`NEO4J_URI`, `NEO4J_PASSWORD`, and `DEEPSEEK_API_KEY`).

## Import convention

Routers import each other as `api.routers.X` and shared models as `api.schemas`. Everything else is a top-level package on `src/backend` (`db`, `agents`, `jobs`, `storage`, `mail`, `citations`, `config`).
