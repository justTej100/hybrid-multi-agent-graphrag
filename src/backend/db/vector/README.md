# vector

This folder prepares textbook text for similarity search. Ingestion calls it while a PDF is becoming searchable. The study pipeline does not import these modules itself. It asks `db.client` to search, and the pgvector adapter uses the embedder defined here.

`__init__.py` marks the package.

`chunking.py` splits extracted pages into chunks. Each chunk has a chunk id, a document id, a page number, and content. That is the shape `PostgresAdapter.add_chunks` stores, and the page number is what later becomes a `[pN]` citation.

`embeddings.py` calls Gemini to embed text. It forces 3072 dimensions so every vector matches the `vector_chunks` column and the HNSW index in `schema.sql`. `config.get_embedder` caches one instance for the process. Tests replace it with a deterministic hash embedder of the same size, so retrieval tests never call Gemini.
