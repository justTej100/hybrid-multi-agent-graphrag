# src/backend/db/PostgresAdapter.py

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row


class PostgresAdapter:
    """
    Application-facing API for PostgreSQL.

    The rest of the application should use this class instead of
    talking directly to PostgreSQL.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(
            self.database_url,
            row_factory=dict_row,
        )

    # -------------------------
    # Documents / Books
    # -------------------------

    def create_document(
        self,
        title: str,
        storage_path: str,
        total_pages: int = 0,
    ) -> str:

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents
                        (title, storage_path, total_pages, status)
                    VALUES
                        (%s, %s, %s, 'processing')
                    RETURNING id
                    """,
                    (title, storage_path, total_pages),
                )

                document_id = cur.fetchone()["id"]

            conn.commit()

        return str(document_id)

    def get_document(self, document_id: str) -> dict[str, Any] | None:

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM documents
                    WHERE id = %s
                    """,
                    (document_id,),
                )

                return cur.fetchone()

    def list_documents(self) -> list[dict[str, Any]]:

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM documents
                    ORDER BY uploaded_at DESC
                    """
                )

                return cur.fetchall()

    def update_document_status(
        self,
        document_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE documents
                    SET
                        status = %s,
                        error_message = %s
                    WHERE id = %s
                    """,
                    (
                        status,
                        error_message,
                        document_id,
                    ),
                )

            conn.commit()

    # -------------------------
    # Chunks
    # -------------------------

    def add_chunks(
        self,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> None:

        with self._connect() as conn:
            with conn.cursor() as cur:

                for chunk in chunks:
                    cur.execute(
                        """
                        INSERT INTO chunks (
                            document_id,
                            chunk_id,
                            page_number,
                            content
                        )
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (chunk_id)
                        DO UPDATE SET
                            content = EXCLUDED.content,
                            page_number = EXCLUDED.page_number
                        """,
                        (
                            document_id,
                            chunk["chunk_id"],
                            chunk["page_number"],
                            chunk["content"],
                        ),
                    )

            conn.commit()

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM chunks
                    WHERE chunk_id = %s
                    """,
                    (chunk_id,),
                )

                return cur.fetchone()

    def get_chunks(
        self,
        document_id: str,
    ) -> list[dict[str, Any]]:

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM chunks
                    WHERE document_id = %s
                    ORDER BY page_number, chunk_id
                    """,
                    (document_id,),
                )

                return cur.fetchall()

    # -------------------------
    # Delete
    # -------------------------

    def delete_document(self, document_id: str) -> None:

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM documents
                    WHERE id = %s
                    """,
                    (document_id,),
                )

            conn.commit()