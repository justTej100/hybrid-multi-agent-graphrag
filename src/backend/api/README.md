# api

This folder is the FastAPI application. `main.py` builds the app. `schemas.py` holds the request and response models the routers share. `routers` holds one module per area of the product.

The process starts here. On startup the lifespan calls `db.client.init_schema`, which creates tables when Postgres is configured. On shutdown it closes pools. Middleware allows credentialed browser calls and signed session cookies. Each router is mounted with no extra path prefix, so routes such as `/chat` and `/documents` are the public URLs.

When `DATABASE_URL` is unset, document, subscription, usage, and session calls stay in memory. When it is set, those calls go to Postgres. Neo4j work stays off unless `kg_enabled` is true.

## Files

`__init__.py` marks this folder as a Python package so `api.main` can be imported.

`main.py` creates the FastAPI app, loads settings by importing `config`, and mounts the routers for auth, documents, chat, flashcards, admin, and graph. `GET /health` returns a status payload for process checks. For a normal browser visit it returns `src/frontend/dist/index.html` on the site paths `/`, `/login`, `/library`, `/study`, `/quiz`, `/flashcards`, and `/admin`. Built JS and CSS are served from `src/frontend/dist/assets`. The graph path is special and is documented in the routers readme, because the same path also returns JSON.

`schemas.py` defines the chat message, the library or single-document scope, the chat request, and the study response the frontend already expects. The chat request may include a session id so an admin follow-up stays on the same thread. Quiz and flashcard payloads ride along in the structured field of the study response.

Routers import each other as `api.routers` and shared models as `api.schemas`. Database, agents, jobs, storage, mail, and citations are imported as top-level packages because `src/backend` is the import root.
