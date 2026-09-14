# src/backend/db/PGvectorAdapter.py

from __future__ import annotations

from typing import Any

import psycopg

from .vector.embeddings import GeminiEmbedder


class PGvectorAdapter:
    """
    Application-facing API for pgvector.

    Responsible for:
    - storing embeddings
    - similarity search
    - deleting document vectors
    """

    def __init__(
        self,
        database_url: str,
        gemini_api_key: str,
    ):

        self.database_url = database_url

        self.embedder = GeminiEmbedder(
            api_key=gemini_api_key
        )

    def _connect(self):
        return psycopg.connect(
            self.database_url
        )

    def add_chunks(
        self,
        chunks: list[dict[str, Any]],
    ) -> None:

        if not chunks:
            return

        texts = [
            chunk["content"]
            for chunk in chunks
        ]

        embeddings = self.embedder.embed_texts(texts)

        with self._connect() as conn:
            with conn.cursor() as cur:

                for chunk, embedding in zip(
                    chunks,
                    embeddings,
                ):

                    cur.execute(
                        """
                        INSERT INTO vector_chunks (
                            chunk_id,
                            document_id,
                            embedding
                        )
                        VALUES (%s, %s, %s)
                        ON CONFLICT (chunk_id)
                        DO UPDATE SET
                            embedding = EXCLUDED.embedding
                        """,
                        (
                            chunk["chunk_id"],
                            chunk["document_id"],
                            embedding,
                        ),
                    )

            conn.commit()

    def similarity_search(
        self,
        query: str,
        limit: int = 10,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:

        query_embedding = self.embedder.embed_text(
            query
        )

        with self._connect() as conn:
            with conn.cursor() as cur:

                if document_id:

                    cur.execute(
                        """
                        SELECT
                            c.chunk_id,
                            c.document_id,
                            c.page_number,
                            c.content,
                            1 - (
                                v.embedding <=> %s::vector
                            ) AS similarity
                        FROM vector_chunks v
                        JOIN chunks c
                            ON c.chunk_id = v.chunk_id
                        WHERE v.document_id = %s
                        ORDER BY
                            v.embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (
                            query_embedding,
                            document_id,
                            query_embedding,
                            limit,
                        ),
                    )

                else:

                    cur.execute(
                        """
                        SELECT
                            c.chunk_id,
                            c.document_id,
                            c.page_number,
                            c.content,
                            1 - (
                                v.embedding <=> %s::vector
                            ) AS similarity
                        FROM vector_chunks v
                        JOIN chunks c
                            ON c.chunk_id = v.chunk_id
                        ORDER BY
                            v.embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (
                            query_embedding,
                            query_embedding,
                            limit,
                        ),
                    )

                return cur.fetchall()

    def delete_document_vectors(
        self,
        document_id: str,
    ) -> None:

        with self._connect() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    DELETE FROM vector_chunks
                    WHERE document_id = %s
                    """,
                    (document_id,),
                )

            conn.commit()