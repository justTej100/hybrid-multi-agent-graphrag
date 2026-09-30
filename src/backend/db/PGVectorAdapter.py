from __future__ import annotations

import uuid
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row


def _vector_literal(values: list[float]) -> str:
    return '[' + ','.join(f'{value:.8f}' for value in values) + ']'


class PGvectorAdapter:
    """Store embeddings and run cosine similarity search over vector_chunks."""

    def __init__(
        self,
        database_url: str,
        gemini_api_key: str | None = None,
        embedder=None,
    ):
        self.database_url = database_url
        if embedder is not None:
            self.embedder = embedder
        else:
            from .vector.embeddings import GeminiEmbedder

            self.embedder = GeminiEmbedder(api_key=gemini_api_key or '')

    def _connect(self):
        conn = psycopg.connect(self.database_url, row_factory=dict_row)
        register_vector(conn)
        return conn

    def add_chunks(self, chunks: list[dict[str, Any]]) -> None:
        if not chunks:
            return
        texts = [chunk.get('content') or chunk.get('text') or '' for chunk in chunks]
        embeddings = self.embedder.embed_texts(texts)
        with self._connect() as conn:
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings):
                    cur.execute(
                        """
                        INSERT INTO vector_chunks (chunk_id, document_id, embedding)
                        VALUES (%s, %s, %s::vector)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding
                        """,
                        (
                            chunk['chunk_id'],
                            str(chunk['document_id']),
                            _vector_literal(list(embedding)),
                        ),
                    )
            conn.commit()

    def similarity_search(
        self,
        query: str,
        limit: int = 10,
        document_ids: list[str] | str | None = None,
    ) -> list[dict[str, Any]]:
        """Return chunk dicts with a `text` field, optionally limited to document ids."""
        if isinstance(document_ids, str):
            document_ids = [document_ids]
        if document_ids is not None and len(document_ids) == 0:
            return []

        literal = _vector_literal(list(self.embedder.embed_text(query)))
        where = ''
        params: list[Any] = [literal]
        if document_ids:
            where = 'WHERE v.document_id = ANY(%s)'
            params.append([uuid.UUID(str(document_id)) for document_id in document_ids])
        params.extend([literal, limit])

        sql = f"""
            SELECT
                c.chunk_id,
                c.document_id,
                c.page_number,
                c.content,
                1 - (v.embedding::halfvec(3072) <=> %s::halfvec(3072)) AS similarity
            FROM vector_chunks v
            JOIN chunks c ON c.chunk_id = v.chunk_id
            {where}
            ORDER BY v.embedding::halfvec(3072) <=> %s::halfvec(3072)
            LIMIT %s
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            content = row['content']
            similarity = row['similarity']
            results.append(
                {
                    'chunk_id': row['chunk_id'],
                    'document_id': str(row['document_id']),
                    'page_number': row['page_number'],
                    'text': content,
                    'content': content,
                    'similarity': float(similarity) if similarity is not None else 0.0,
                }
            )
        return results

    def delete_document_vectors(self, document_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'DELETE FROM vector_chunks WHERE document_id = %s',
                    (document_id,),
                )
            conn.commit()
