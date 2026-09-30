# db

This folder stores textbooks and finds passages for an answer. The rest of the app talks to `client.py`. That module is an async facade. With `DATABASE_URL` set it calls Postgres on a worker thread. Without it, documents, chunks, and study sessions live in process memory so the app and the fast tests run with no Docker.

Three stores sit behind that facade.

Postgres holds documents, page chunks, flashcard subscriptions, guest chat usage, and admin study sessions.

pgvector holds one embedding per chunk. Search casts those vectors to halfvec because an HNSW index on a full 3072-dimension `vector` column is not allowed.

Neo4j holds entities and relationships extracted from pages. It is optional. `KnowledgeGraphAdapter` is constructed only when `kg_enabled` is true.

Supabase, when configured, stores the original PDF bytes. The relational row only keeps the storage path.

## Files

`__init__.py` marks the package.

`schema.sql` is applied on startup. It creates the vector extension, the documents table, chunks, vector chunks, flashcard subscriptions, chat usage, and the admin study tables. Documents track title, description, status, page count, scan warning, flashcard signup, and error text. `study_sessions` stores the owner email, title, mode, scope, and update time. `study_messages` stores role, content, sources, structured output, and time. The embedding index is HNSW on the halfvec cast of the 3072-dimension column.

`client.py` is the API the routers and the study pipeline use. It creates and lists documents, updates status, deletes them, adds chunks, searches chunks inside an allowed set of document ids, counts vectors, samples chunks for the admin page, and creates, lists, fetches, and appends study sessions. `get_pool` is the asyncpg pool used by subscriptions and the rate limiter. `get_kg_adapter` returns the Neo4j adapter or nothing. `reset_memory` clears the in-memory store in tests. `set_embedder` and `set_kg_extractor` install test doubles.

`PostgresAdapter.py` is the synchronous SQL for documents, chunks, and study sessions. `client.py` calls it through a thread. Session rows store scope, sources, and structured output as JSON.

`PGVectorAdapter.py` embeds chunks and runs similarity search limited to the document ids the question is allowed to see. Results are chunk id, document id, page number, text, and similarity. Deletes follow the document.

`KnowledgeGraphAdapter.py` extracts a page into the graph and searches it. `search_related_concepts` matches when the query contains an entity name or the name contains the query, with an optional book filter. `list_graph` returns a capped set of names, types, descriptions, book ids, pages, and relationships with evidence for the Graph tab. `extract_and_store` is what ingestion calls per page.

`subscriptions.py` opens or closes flashcard signup on a textbook, lists offers, subscribes and unsubscribes an email, and lists subscriber addresses for a broadcast. It uses Postgres when the pool exists and memory otherwise.

`pdf.py` reads page text from a PDF with PyMuPDF. Ingestion uses it before chunking.

`storage.py` is the Supabase Storage client for PDF bytes. The top-level `storage.py` calls it when the backend is not local.

## Folders

`vector` builds embeddings and splits pages into chunks. See its readme.

`knowledge_graph` talks to Neo4j and to the extraction model. See its readme.

Ingestion in `jobs.py` is the writer. It calls `pdf.py`, `vector/chunking.py`, `PostgresAdapter.add_chunks`, `PGVectorAdapter.add_chunks`, and, when enabled, `KnowledgeGraphAdapter.extract_and_store`. The study pipeline is the reader. It calls `client.search_chunks` and, when enabled, graph search.
