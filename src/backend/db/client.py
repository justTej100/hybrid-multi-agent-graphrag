from __future__ import annotations

"""Async document/chunk API used by the routers.

Talks to PostgreSQL when DATABASE_URL is set. Otherwise keeps documents,
chunks, and (via subscriptions.py / rate_limit.py) the rest of the product
state in memory so the app and the fast tests run without Docker.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from config import database_url, set_embedder as _config_set_embedder

logger = logging.getLogger(__name__)

_memory_documents: dict[str, dict[str, Any]] = {}
_memory_chunks: list[dict[str, Any]] = []
_memory_sessions: dict[str, dict[str, Any]] = {}
_pool = None
_pool_failed = False
_pg = None
_vector = None
_kg = None
_kg_extractor = None


def using_postgres() -> bool:
    return bool(database_url())


def reset_memory() -> None:
    """Clear the in-memory document store (tests)."""
    global _pool_failed
    _memory_documents.clear()
    _memory_chunks.clear()
    _memory_sessions.clear()
    _pool_failed = False


def set_embedder(embedder) -> None:
    """Install a shared embedder and drop any vector adapter built with the old one."""
    global _vector
    _config_set_embedder(embedder)
    _vector = None


def set_kg_extractor(extractor) -> None:
    """Install a graph extractor and drop any adapter that captured the previous one."""
    global _kg_extractor, _kg
    _kg_extractor = extractor
    if _kg is not None:
        try:
            _kg.close()
        except Exception:
            logger.debug('Failed to close the previous knowledge-graph adapter', exc_info=True)
        _kg = None


def _postgres():
    global _pg
    url = database_url()
    if not url:
        raise RuntimeError('DATABASE_URL is not set.')
    if _pg is None or _pg.database_url != url:
        from db.PostgresAdapter import PostgresAdapter

        _pg = PostgresAdapter(url)
    return _pg


def get_vector_adapter():
    global _vector
    url = database_url()
    if not url:
        raise RuntimeError('DATABASE_URL is not set.')
    if _vector is None or _vector.database_url != url:
        from config import get_embedder
        from db.PGVectorAdapter import PGvectorAdapter

        _vector = PGvectorAdapter(url, embedder=get_embedder())
    return _vector


def get_kg_adapter():
    """Return the Neo4j adapter when the knowledge graph is configured, else None."""
    global _kg
    from config import deepseek_api_key, kg_enabled, neo4j_settings

    if not kg_enabled():
        return None
    if _kg is None:
        from db.KnowledgeGraphAdapter import KnowledgeGraphAdapter

        settings = neo4j_settings()
        _kg = KnowledgeGraphAdapter(
            settings['uri'],
            settings['username'],
            settings['password'],
            deepseek_api_key(),
            extractor=_kg_extractor,
        )
    return _kg


def _normalize_document(row: dict[str, Any]) -> dict[str, Any]:
    document = dict(row)
    document['id'] = str(document['id'])
    document.setdefault('description', None)
    document.setdefault('has_scan_warning', False)
    document.setdefault('flashcards_open', False)
    document.setdefault('error_message', None)
    return document


async def init_schema() -> None:
    """Apply schema.sql. No-op when there is no database."""
    url = database_url()
    if not url:
        return
    from pathlib import Path

    import psycopg

    sql = (Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8')
    statements = [part.strip() for part in sql.split(';') if part.strip() and not part.isspace()]

    def _apply() -> None:
        with psycopg.connect(url, autocommit=True) as conn:
            for statement in statements:
                conn.execute(statement)

    await asyncio.to_thread(_apply)


async def get_pool():
    """asyncpg pool for chat_usage and flashcard subscriptions, or None in memory mode."""
    global _pool, _pool_failed
    url = database_url()
    if not url or _pool_failed:
        return None
    if _pool is not None:
        return _pool
    try:
        import asyncpg

        dsn = url.replace('postgres://', 'postgresql://', 1)
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return _pool
    except Exception:
        logger.warning('asyncpg pool unavailable; falling back where possible', exc_info=True)
        _pool_failed = True
        _pool = None
        return None


async def shutdown() -> None:
    """Close pooled connections opened during the process lifetime."""
    global _pool, _kg
    if _pool is not None:
        await _pool.close()
        _pool = None
    if _kg is not None:
        adapter = _kg
        _kg = None
        await asyncio.to_thread(adapter.close)


async def create_document(
    title: str,
    description: str | None = None,
    status: str = 'processing',
    total_pages: int = 0,
    storage_path: str = '',
) -> str:
    if not using_postgres():
        document_id = str(uuid4())
        _memory_documents[document_id] = {
            'id': document_id,
            'title': title,
            'description': description,
            'status': status,
            'total_pages': total_pages,
            'storage_path': storage_path,
            'has_scan_warning': False,
            'error_message': None,
            'flashcards_open': False,
            'uploaded_at': datetime.now(timezone.utc),
        }
        return document_id
    return await asyncio.to_thread(
        _postgres().create_document,
        title,
        description,
        status,
        total_pages,
        storage_path,
    )


async def get_document(document_id: str) -> dict[str, Any] | None:
    if not using_postgres():
        document = _memory_documents.get(str(document_id))
        return document
    row = await asyncio.to_thread(_postgres().get_document, document_id)
    return _normalize_document(row) if row else None


async def list_documents() -> list[dict[str, Any]]:
    if not using_postgres():
        documents = list(_memory_documents.values())
        documents.sort(key=lambda document: document.get('uploaded_at') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return documents
    rows = await asyncio.to_thread(_postgres().list_documents)
    return [_normalize_document(row) for row in rows]


async def update_document_status(
    document_id: str,
    status: str,
    error_message: str | None = None,
    storage_path: str | None = None,
    total_pages: int | None = None,
    has_scan_warning: bool | None = None,
) -> None:
    fields: dict[str, Any] = {'status': status}
    if error_message is not None:
        fields['error_message'] = error_message
    if storage_path is not None:
        fields['storage_path'] = storage_path
    if total_pages is not None:
        fields['total_pages'] = total_pages
    if has_scan_warning is not None:
        fields['has_scan_warning'] = has_scan_warning

    if not using_postgres():
        document = _memory_documents.get(str(document_id))
        if document is None:
            return
        document.update(fields)
        return
    await asyncio.to_thread(_postgres().update_document, document_id, **fields)


async def delete_document(document_id: str) -> None:
    from db.subscriptions import delete_subscriptions_for_document

    await delete_subscriptions_for_document(document_id)
    if not using_postgres():
        _memory_documents.pop(str(document_id), None)
        _memory_chunks[:] = [chunk for chunk in _memory_chunks if str(chunk['document_id']) != str(document_id)]
        return
    await asyncio.to_thread(_postgres().delete_document, document_id)


async def add_chunks(document_id: str, chunks: list[dict[str, Any]]) -> None:
    """Persist chunk text and, when Postgres is configured, its embedding."""
    if not chunks:
        return
    if not using_postgres():
        for chunk in chunks:
            text = chunk.get('content') or chunk.get('text') or ''
            _memory_chunks.append(
                {
                    'chunk_id': chunk['chunk_id'],
                    'document_id': str(document_id),
                    'page_number': chunk['page_number'],
                    'content': text,
                    'text': text,
                }
            )
        return
    await asyncio.to_thread(_postgres().add_chunks, document_id, chunks)
    await asyncio.to_thread(get_vector_adapter().add_chunks, chunks)


async def get_scope_document_ids(scope: dict | None) -> list[str]:
    """Document ids a query is allowed to retrieve. Only ready documents qualify."""
    documents = await list_documents()
    ready = [str(document['id']) for document in documents if document.get('status') == 'ready']
    if not scope or scope.get('type', 'library') == 'library':
        return ready
    document_id = scope.get('document_id')
    if document_id and str(document_id) in ready:
        return [str(document_id)]
    return []


def _memory_search(query: str, document_ids: list[str], limit: int) -> list[dict[str, Any]]:
    allowed = {str(document_id) for document_id in document_ids}
    query_tokens = set(re.findall(r'[a-z0-9]+', query.lower()))
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in _memory_chunks:
        if str(chunk['document_id']) not in allowed:
            continue
        text = chunk.get('text') or chunk.get('content') or ''
        tokens = set(re.findall(r'[a-z0-9]+', text.lower()))
        score = (len(query_tokens & tokens) / len(query_tokens)) if query_tokens else 0.0
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, chunk in scored[:limit]:
        text = chunk.get('text') or chunk.get('content') or ''
        results.append(
            {
                'chunk_id': chunk['chunk_id'],
                'document_id': str(chunk['document_id']),
                'page_number': chunk['page_number'],
                'text': text,
                'content': text,
                'similarity': score,
            }
        )
    return results


async def search_chunks(query: str, document_ids: list[str], limit: int = 12) -> list[dict[str, Any]]:
    if not document_ids:
        return []
    if not using_postgres():
        return _memory_search(query, document_ids, limit)
    return await asyncio.to_thread(get_vector_adapter().similarity_search, query, limit, document_ids)


async def count_vectors() -> int:
    if not using_postgres():
        return len(_memory_chunks)
    return await asyncio.to_thread(_postgres().count_vectors)


async def count_vectors_for_document(document_id: str) -> int:
    if not using_postgres():
        return sum(1 for chunk in _memory_chunks if str(chunk['document_id']) == str(document_id))
    return await asyncio.to_thread(_postgres().count_vectors, document_id)


async def sample_chunks(document_id: str, limit: int = 5) -> list[dict[str, Any]]:
    if not using_postgres():
        rows = [chunk for chunk in _memory_chunks if str(chunk['document_id']) == str(document_id)]
    else:
        rows = await asyncio.to_thread(_postgres().get_chunks, document_id, limit)
    samples = []
    for chunk in rows[:limit]:
        text = chunk.get('text') or chunk.get('content') or ''
        samples.append(
            {
                'chunk_id': chunk['chunk_id'],
                'document_id': str(chunk['document_id']),
                'page_number': chunk['page_number'],
                'text': text,
            }
        )
    return samples


def _public_session(session: dict[str, Any], include_messages: bool) -> dict[str, Any]:
    payload = {
        'id': str(session['id']),
        'email': session['email'],
        'title': session['title'],
        'mode': session['mode'],
        'scope': session.get('scope') or {},
        'updated_at': session['updated_at'],
        'message_count': session.get('message_count', len(session.get('messages') or [])),
    }
    if include_messages:
        payload['messages'] = [
            {
                'id': str(message['id']),
                'role': message['role'],
                'content': message['content'],
                'sources': message.get('sources'),
                'structured': message.get('structured'),
                'created_at': message['created_at'],
            }
            for message in session.get('messages') or []
        ]
    return payload


async def create_study_session(email: str, title: str, mode: str, scope: dict) -> str:
    if not using_postgres():
        session_id = str(uuid4())
        _memory_sessions[session_id] = {
            'id': session_id,
            'email': email,
            'title': title[:160] or 'Study',
            'mode': mode,
            'scope': scope,
            'updated_at': datetime.now(timezone.utc),
            'messages': [],
        }
        return session_id
    return await asyncio.to_thread(_postgres().create_study_session, email, title[:160] or 'Study', mode, scope)


async def append_study_message(
    session_id: str,
    role: str,
    content: str,
    sources: list | None = None,
    structured: dict | None = None,
) -> None:
    if not using_postgres():
        session = _memory_sessions.get(session_id)
        if session is None:
            return
        session['messages'].append(
            {
                'id': str(uuid4()),
                'role': role,
                'content': content,
                'sources': sources,
                'structured': structured,
                'created_at': datetime.now(timezone.utc),
            }
        )
        session['updated_at'] = datetime.now(timezone.utc)
        return
    await asyncio.to_thread(_postgres().append_study_message, session_id, role, content, sources, structured)


async def list_study_sessions(email: str) -> list[dict[str, Any]]:
    if not using_postgres():
        rows = [session for session in _memory_sessions.values() if session['email'] == email]
        rows.sort(key=lambda session: session['updated_at'], reverse=True)
        return [_public_session(session, include_messages=False) for session in rows]
    rows = await asyncio.to_thread(_postgres().list_study_sessions, email)
    return [_public_session(row, include_messages=False) for row in rows]


async def get_study_session(session_id: str, email: str) -> dict[str, Any] | None:
    if not using_postgres():
        session = _memory_sessions.get(session_id)
        if session is None or session['email'] != email:
            return None
        return _public_session(session, include_messages=True)
    row = await asyncio.to_thread(_postgres().get_study_session, session_id, email)
    if row is None:
        return None
    return _public_session(row, include_messages=True)
