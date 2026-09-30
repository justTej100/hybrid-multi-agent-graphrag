# tests

This folder proves the backend behaves as the product describes. The frontend is checked with `npm run build` in `src/frontend`, which typechecks the screens against `api.ts`.

`pytest.ini` at the repo root puts `src/backend` on the import path, runs async tests in auto mode, and skips anything marked integration unless you ask for it. `make test` is the fast suite. `make test-integration` is the Docker suite.

`conftest.py` runs before the fast tests. It blocks the developer `.env` from loading, clears the database URL and Neo4j settings, points storage at a temp folder, installs the fake chat model, and resets in-memory documents, subscriptions, and chat usage. `authenticated_client` signs in as the admin. `guest_client` signs in as a guest. They share one cookie jar, so one test should not request both.

`fakes.py` holds the stand-ins. The fake chat model supports the LangChain calls the pipeline makes and returns scripted chat, quiz, flashcard, and summary payloads. The hash embedder fills 3072 dimensions so vector code can run without Gemini. The fake graph extractor returns a small fixed entity and relationship. `make_pdf` builds a one-page PDF with PyMuPDF for upload tests.

## Folders

`unit` checks single modules with no HTTP server. See its readme.

`api` checks the routes through the FastAPI test client and the in-memory database. See its readme.

`integration` checks the same routes against real Postgres and, for one test, real Neo4j. See its readme.

Together they cover sign-in, uploads, ingestion, all four study modes, guest limits, flashcard signup, admin stats, admin-only session save, and the graph route when Neo4j is off.
