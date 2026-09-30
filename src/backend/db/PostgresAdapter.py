from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

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

    def create_study_session(self, email: str, title: str, mode: str, scope: dict) -> str:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO study_sessions (email, title, mode, scope)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (email, title, mode, Json(scope)),
                )
                session_id = cur.fetchone()['id']
            conn.commit()
        return str(session_id)

    def append_study_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: list | None,
        structured: dict | None,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO study_messages (session_id, role, content, sources, structured)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        session_id,
                        role,
                        content,
                        Json(sources) if sources is not None else None,
                        Json(structured) if structured is not None else None,
                    ),
                )
                cur.execute(
                    'UPDATE study_sessions SET updated_at = NOW() WHERE id = %s',
                    (session_id,),
                )
            conn.commit()

    def list_study_sessions(self, email: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.email, s.title, s.mode, s.scope, s.updated_at,
                           (SELECT COUNT(*) FROM study_messages m WHERE m.session_id = s.id) AS message_count
                    FROM study_sessions s
                    WHERE s.email = %s
                    ORDER BY s.updated_at DESC
                    """,
                    (email,),
                )
                return [dict(row) for row in cur.fetchall()]

    def get_study_session(self, session_id: str, email: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, title, mode, scope, updated_at
                    FROM study_sessions
                    WHERE id = %s AND email = %s
                    """,
                    (session_id, email),
                )
                row = cur.fetchone()
                if not row:
                    return None
                session = dict(row)
                cur.execute(
                    """
                    SELECT id, role, content, sources, structured, created_at
                    FROM study_messages
                    WHERE session_id = %s
                    ORDER BY created_at, id
                    """,
                    (session_id,),
                )
                session['messages'] = [dict(message) for message in cur.fetchall()]
        return session
