CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    title TEXT NOT NULL,

    storage_path TEXT NOT NULL,

    total_pages INTEGER NOT NULL DEFAULT 0,

    status TEXT NOT NULL
        CHECK (status IN (
            'processing',
            'ready',
            'error'
        )),

    error_message TEXT,

    uploaded_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,

    document_id UUID NOT NULL
        REFERENCES documents(id)
        ON DELETE CASCADE,

    page_number INTEGER NOT NULL,

    content TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS vector_chunks (
    chunk_id TEXT PRIMARY KEY
        REFERENCES chunks(chunk_id)
        ON DELETE CASCADE,

    document_id UUID NOT NULL
        REFERENCES documents(id)
        ON DELETE CASCADE,

    embedding vector(3072)
);


CREATE INDEX IF NOT EXISTS chunks_document_idx
ON chunks(document_id);


CREATE INDEX IF NOT EXISTS vector_chunks_document_idx
ON vector_chunks(document_id);


CREATE INDEX IF NOT EXISTS vector_chunks_embedding_idx
ON vector_chunks
USING hnsw (embedding vector_cosine_ops);