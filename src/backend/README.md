# backend

This is the import root for the API. Run uvicorn with the app directory set to `src/backend`, module `api.main`, application object `app`, port 8000. The Makefile target `app` does that.

Nothing in this folder draws a page by itself, except that `api/main.py` returns the built React files for the site routes. Everything else answers JSON, stores files, or prepares textbook data for those answers.

## Files

`config.py` loads the repo-root `.env` and exposes the settings the rest of the process needs. That includes the database URL, Gemini and DeepSeek keys, Neo4j settings, and `kg_enabled`, which is true only when Neo4j URI, Neo4j password, and the DeepSeek key are all set. It also builds the shared embedder. Tests replace that embedder so Gemini is not called.

`citations.py` finds `[pN]` markers, checks them against retrieved pages, and builds the page links used in flashcard email. Agents and mail import it from here so they do not depend on the HTTP layer.

`jobs.py` is the ingestion worker. `schedule_ingestion` starts a background task for one uploaded PDF. The task downloads the file, extracts pages, flags scans, chunks text, stores chunks and embeddings, and, when the graph is enabled, extracts a graph per page. It then marks the document ready or error. `ARGUS_INGEST_INLINE` makes the upload request wait until that work finishes, which is what tests use. `wait_for_jobs` lets a caller wait on the in-process tasks.

`storage.py` saves, loads, and deletes PDF bytes. With `STORAGE_BACKEND` set to `local`, files go under `uploaded_pdfs` in this folder. Otherwise it uses the Supabase client in `db/storage.py`. Upload and download errors surface as `StorageError`. It also builds the dashboard URLs the admin page shows.

`requirements.txt` is the Python dependency list `make install` installs. It includes FastAPI, the LangGraph stack, the Gemini and OpenAI clients, Neo4j, Postgres, and pytest.

## Folders

`api` is the HTTP surface. See its readme.

`agents` is the study loop that turns a question into an answer. See its readme.

`db` is Postgres, pgvector, Neo4j, and the in-memory stand-in. See its readme.

`mail` sends flashcard decks. See its readme.

The routers call `jobs` after an upload, `storage` when a PDF must be read or written, `db.client` for documents and sessions, `agents.service` for answers, and `mail` when a deck should be emailed.
