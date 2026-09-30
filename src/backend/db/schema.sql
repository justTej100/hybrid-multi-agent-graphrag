CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    storage_path TEXT NOT NULL,
    total_pages INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL
        CHECK (status IN ('processing', 'ready', 'error')),
    error_message TEXT,
    has_scan_warning BOOLEAN NOT NULL DEFAULT false,
    flashcards_open BOOLEAN NOT NULL DEFAULT false,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Upgrade databases created before description / flashcard columns existed.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS has_scan_warning BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS flashcards_open BOOLEAN NOT NULL DEFAULT false;

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

CREATE TABLE IF NOT EXISTS flashcard_subscriptions (
    document_id UUID NOT NULL
        REFERENCES documents(id)
        ON DELETE CASCADE,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (document_id, email)
);

CREATE TABLE IF NOT EXISTS chat_usage (
    email TEXT PRIMARY KEY,
    last_chat_at TIMESTAMPTZ,
    day_date DATE,
    day_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS chunks_document_idx
ON chunks(document_id);

CREATE INDEX IF NOT EXISTS vector_chunks_document_idx
ON vector_chunks(document_id);

-- pgvector refuses HNSW indexes on vector columns above 2000 dimensions.
-- Index the halfvec cast instead, and use the same expression in search.
CREATE INDEX IF NOT EXISTS vector_chunks_embedding_idx
ON vector_chunks
USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops);
