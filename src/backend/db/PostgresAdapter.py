from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

_UPDATABLE = {
    'status',
    'error_message',
    'storage_path',
    'total_pages',
    'has_scan_warning',
    'description',
    'flashcards_open',
    'title',
}


class PostgresAdapter:
    """Synchronous PostgreSQL access for documents, chunks, and counts."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def create_document(
        self,
        title: str,
        description: str | None,
        status: str,
        total_pages: int,
        storage_path: str,
    ) -> str:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents
                        (title, description, storage_path, total_pages, status)
                    VALUES
                        (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (title, description, storage_path, total_pages, status),
                )
                document_id = cur.fetchone()['id']
            conn.commit()
        return str(document_id)

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT * FROM documents WHERE id = %s',
                    (document_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def list_documents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT * FROM documents ORDER BY uploaded_at DESC',
                )
                return [dict(row) for row in cur.fetchall()]

    def update_document(self, document_id: str, **fields: Any) -> None:
        assignments: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            if key not in _UPDATABLE:
                continue
            assignments.append(f'{key} = %s')
            values.append(value)
        if not assignments:
            return
        values.append(document_id)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE documents SET {', '.join(assignments)} WHERE id = %s",
                    values,
                )
            conn.commit()

    def add_chunks(self, document_id: str, chunks: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                for chunk in chunks:
                    cur.execute(
                        """
                        INSERT INTO chunks (document_id, chunk_id, page_number, content)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            content = EXCLUDED.content,
                            page_number = EXCLUDED.page_number
                        """,
                        (
                            document_id,
                            chunk['chunk_id'],
                            chunk['page_number'],
                            chunk.get('content') or chunk.get('text') or '',
                        ),
                    )
            conn.commit()

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM chunks WHERE chunk_id = %s', (chunk_id,))
                row = cur.fetchone()
        return dict(row) if row else None

    def get_chunks(self, document_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT * FROM chunks
            WHERE document_id = %s
            ORDER BY page_number, chunk_id
        """
        params: list[Any] = [document_id]
        if limit is not None:
            sql += ' LIMIT %s'
            params.append(limit)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]

    def count_vectors(self, document_id: str | None = None) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if document_id:
                    cur.execute(
                        'SELECT COUNT(*) AS n FROM vector_chunks WHERE document_id = %s',
                        (document_id,),
                    )
                else:
                    cur.execute('SELECT COUNT(*) AS n FROM vector_chunks')
                return int(cur.fetchone()['n'])

    def delete_document(self, document_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM documents WHERE id = %s', (document_id,))
            conn.commit()
