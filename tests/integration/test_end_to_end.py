from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from fakes import make_pdf
from integration_services import NEO4J_PASSWORD, NEO4J_URI, POSTGRES_URL, neo4j_or_skip

pytestmark = pytest.mark.integration

VARIANCE = (
    'Variance measures the spread of data around the mean. '
    'A larger variance means the observations are more dispersed.'
)
MITO = 'Mitochondria produce energy inside a living cell and are not a statistics concept.'


def _counts(document_id: str) -> tuple[int, int]:
    with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) AS n FROM chunks WHERE document_id = %s', (document_id,))
            chunks = int(cur.fetchone()['n'])
            cur.execute('SELECT COUNT(*) AS n FROM vector_chunks WHERE document_id = %s', (document_id,))
            vectors = int(cur.fetchone()['n'])
    return chunks, vectors


def _upload(client, title: str, text: str) -> str:
    response = client.post(
        '/documents',
        files={'file': (f'{title}.pdf', make_pdf(text), 'application/pdf')},
        data={'title': title, 'description': title},
    )
    assert response.status_code == 200, response.text
    return response.json()['id']


def test_schema_ingestion_chat_and_cascade(integration_client) -> None:
    with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'documents'
                """
            )
            columns = {row['column_name'] for row in cur.fetchall()}
    assert {'description', 'has_scan_warning', 'flashcards_open'} <= columns

    document_id = _upload(integration_client, 'Statistics', VARIANCE)
    status = integration_client.get(f'/documents/{document_id}/status')
    assert status.status_code == 200
    assert status.json()['status'] == 'ready'
    chunks, vectors = _counts(document_id)
    assert chunks >= 1
    assert vectors == chunks

    other_id = _upload(integration_client, 'Biology', MITO)
    scoped = integration_client.post(
        '/chat',
        json={
            'messages': [{'role': 'user', 'content': 'What is variance?'}],
            'mode': 'chat',
            'scope': {'type': 'document', 'document_id': document_id},
        },
    )
    assert scoped.status_code == 200, scoped.text
    body = scoped.json()
    assert body['sources']
    assert {source['document_id'] for source in body['sources']} == {document_id}
    assert body['eval']['citation_errors'] == []
    assert '[p' in body['brief']
    cited_pages = {source['page_number'] for source in body['sources']}
    assert any(f'[p{page}]' in body['brief'] for page in cited_pages)

    other = integration_client.post(
        '/chat',
        json={
            'messages': [{'role': 'user', 'content': 'What is variance?'}],
            'mode': 'chat',
            'scope': {'type': 'document', 'document_id': other_id},
        },
    )
    assert other.status_code == 200
    assert {source['document_id'] for source in other.json()['sources']} == {other_id}

    assert integration_client.delete(f'/documents/{document_id}').status_code == 200
    assert _counts(document_id) == (0, 0)


def test_subscriptions_and_rate_limit_persist(integration_client) -> None:
    from api.routers.auth import COOKIE_NAME, issue_session_token

    document_id = _upload(integration_client, 'Statistics', VARIANCE)
    opened = integration_client.patch(f'/documents/{document_id}/flashcards-open', json={'enabled': True})
    assert opened.status_code == 200

    integration_client.cookies.set(COOKIE_NAME, issue_session_token('guest@example.com'))
    subscribed = integration_client.post('/flashcards/subscribe', json={'document_id': document_id})
    assert subscribed.status_code == 200, subscribed.text

    with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT email FROM flashcard_subscriptions WHERE document_id = %s',
                (document_id,),
            )
            emails = [row['email'] for row in cur.fetchall()]
    assert emails == ['guest@example.com']

    payload = {
        'messages': [{'role': 'user', 'content': 'What is variance?'}],
        'mode': 'chat',
        'scope': {'type': 'library'},
    }
    assert integration_client.post('/chat', json=payload).status_code == 200
    limited = integration_client.post('/chat', json=payload)
    assert limited.status_code == 429

    with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT day_count FROM chat_usage WHERE email = 'guest@example.com'")
            row = cur.fetchone()
    assert row is not None
    assert int(row['day_count']) == 1


def test_knowledge_graph_ingestion_and_search(integration_client, monkeypatch) -> None:
    neo4j_or_skip()
    monkeypatch.setenv('NEO4J_URI', NEO4J_URI)
    monkeypatch.setenv('NEO4J_USERNAME', 'neo4j')
    monkeypatch.setenv('NEO4J_PASSWORD', NEO4J_PASSWORD)
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'fake-key')

    from db.client import get_kg_adapter, set_kg_extractor
    from fakes import FakeGraphExtractor

    set_kg_extractor(FakeGraphExtractor())
    adapter = get_kg_adapter()
    assert adapter is not None
    adapter.neo4j.query('MATCH (n) DETACH DELETE n')

    document_id = _upload(integration_client, 'Statistics', VARIANCE)
    rows = adapter.search_related_concepts('what is variance', limit=10, book_id=document_id)
    assert rows
    assert any(row['source'] == 'variance' and row['target'] == 'data' for row in rows)

    import asyncio

    from agents.QueryAgent import _run_graph_search

    facts = asyncio.run(_run_graph_search('what is variance', {'type': 'document', 'document_id': document_id}))
    assert 'variance' in facts.lower()
    assert 'data' in facts.lower()
    adapter.close()
    import db.client as client_mod

    client_mod._kg = None
