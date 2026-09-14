# `api/` — Backend structure

FastAPI backend for Argus. `main.py` only wires things together; every
route, model, and helper lives inside `router/`.

```
api/
├── main.py               # App creation, lifespan, middleware, router mounting, SPA serving
├── schemas.py            # All Pydantic request/response models, shared across routers
└── router/
    ├── __init__.py
    ├── auth.py            # Session-cookie helpers + Google OAuth + /me + /logout
    ├── documents.py       # Upload, list, status, delete, bulk-delete, file download, flashcards-open
    ├── chat.py            # /chat and /search (study Q&A pipeline)
    ├── flashcards.py      # Flashcard email, subscribe/unsubscribe, admin broadcast
    ├── admin.py           # Admin dashboard: config, stats, chunk inspection
    ├── meta.py            # /health
    ├── citations.py       # [pN] page-citation parsing/linking (used across routers + eval)
    └── rate_limit.py      # Guest chat cooldown + daily cap
```

## `main.py`

Owns app-level concerns only:
- Creates the `FastAPI` app and lifespan (`init_schema`, `ensure_vector_table` on startup)
- Registers `CORSMiddleware` and `SessionMiddleware`
- Includes every router from `router/`
- Serves the React SPA (`/`, `/login`, `/study`, `/admin` → `index.html`) and mounts `/assets`

It has no route logic of its own beyond SPA fallback — if you're looking
for an actual API endpoint's implementation, it's in `router/`.

## `schemas.py`

Every Pydantic model shared across more than one router: `ChatRequest`,
`Scope`, `StudyResponse`, `EvalResponse`, the flashcard request bodies, and
`BulkDeleteRequest`. Kept at the top level (not inside `router/`) since it's
pure data shape, not a router.

## `router/`

### `auth.py`
Two things live here together because they're both "auth":
- **Session helpers** (`require_session`, `require_admin`, `get_session_email`,
  `set_session_cookie`, etc.) — imported as FastAPI dependencies by every
  other router that needs to gate a route.
- **Routes**: `GET /auth/google`, `GET /auth/google/callback`, `GET /logout`,
  `GET /me`.

### `documents.py`
Everything that treats a document as a resource: `GET/POST /documents`,
`GET /documents/{id}/status`, `DELETE /documents/{id}`,
`POST /documents/bulk-delete`, `GET /documents/{id}/file`,
`PATCH /documents/{id}/flashcards-open`.

### `chat.py`
The study/tutoring endpoints: `POST /chat` (runs the RAG pipeline via
`agents.Pipeline.ResearchPipeline`) and `POST /search` (alias for `/chat`).
Also owns the "email flashcards after a flashcard-mode chat" side effect.

### `flashcards.py`
Everything about flashcard delivery and subscriptions:
`POST /flashcards/email`, `GET /flashcards/offers`,
`POST /flashcards/subscribe`, `POST /flashcards/unsubscribe`,
`POST /flashcards/broadcast`. (Toggling whether flashcards are open for a
document lives in `documents.py` instead, since it mutates a document field.)

### `admin.py`
Admin-only dashboard data: `GET /admin/config`, `GET /admin/stats`,
`GET /admin/documents/{id}/chunks`. All routes here require admin via a
router-level dependency.

### `meta.py`
Just `GET /health`.

### `citations.py`
Not a router — a utility module for parsing/generating `[pN]` page-citation
tags. Used by `chat.py`'s pipeline results, `EvalAgent`-style checks, and
flashcard emails.

### `rate_limit.py`
Not a router — guest chat cooldown + daily cap logic (`chat_usage` table or
in-memory fallback). Used by `chat.py` and `auth.py` (`/me`'s usage status).

## Import convention

Anything inside `router/` that needs another router-local module imports it
as `router.X` (e.g. `from router.auth import require_session`). Anything
that needs `schemas.py` imports it as a top-level module
(`from schemas import ChatRequest`), since `schemas.py` sits next to
`main.py`, not inside `router/`.