from __future__ import annotations

import pytest
import psycopg
from fastapi.testclient import TestClient

POSTGRES_URL = 'postgresql://argus:test@127.0.0.1:55432/argus'
NEO4J_URI = 'bolt://127.0.0.1:7688'
NEO4J_PASSWORD = 'testpassword'


def postgres_or_skip() -> None:
    try:
        with psycopg.connect(POSTGRES_URL, connect_timeout=3) as conn:
            conn.execute('SELECT 1')
    except Exception as exc:
        pytest.skip(
            f'Postgres is not reachable ({exc}). '
            'Start it with: docker compose -f docker-compose.test.yml up -d'
        )


def neo4j_or_skip() -> None:
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(NEO4J_URI, auth=('neo4j', NEO4J_PASSWORD))
        driver.verify_connectivity()
        driver.close()
    except Exception as exc:
        pytest.skip(
            f'Neo4j is not reachable ({exc}). '
            'Start it with: docker compose -f docker-compose.test.yml up -d'
        )


def truncate() -> None:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as conn:
        conn.execute('TRUNCATE TABLE documents, chat_usage, study_sessions RESTART IDENTITY CASCADE')


@pytest.fixture
def integration_client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> TestClient:
    postgres_or_skip()
    monkeypatch.setenv('DATABASE_URL', POSTGRES_URL)
    monkeypatch.setenv('NEO4J_URI', '')
    monkeypatch.setenv('NEO4J_PASSWORD', '')
    monkeypatch.setenv('DEEPSEEK_API_KEY', '')
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('ADMIN_EMAIL', 'admin@test.com')
    monkeypatch.setenv('STORAGE_BACKEND', 'local')
    monkeypatch.setenv('ARGUS_INGEST_INLINE', '1')
    monkeypatch.setenv('GUEST_CHAT_COOLDOWN_SECONDS', '300')
    monkeypatch.setenv('GUEST_CHAT_DAILY_LIMIT', '10')
    monkeypatch.setenv('GMAIL_USER', '')
    monkeypatch.setenv('GMAIL_APP_PASSWORD', '')

    import storage
    from agents.service import set_llm
    from api.main import app
    from api.routers.auth import COOKIE_NAME, issue_session_token
    from api.routers.rate_limit import reset_memory_usage
    from db.client import reset_memory, set_embedder, set_kg_extractor
    from db.subscriptions import reset_memory_subscriptions
    from fakes import FakeChatModel, FakeGraphExtractor, HashEmbedder

    monkeypatch.setattr(storage, 'LOCAL_UPLOAD_DIR', tmp_path)
    reset_memory()
    reset_memory_subscriptions()
    reset_memory_usage()
    set_embedder(HashEmbedder())
    set_kg_extractor(FakeGraphExtractor())
    set_llm(FakeChatModel())

    with TestClient(app) as test_client:
        truncate()
        test_client.cookies.set(COOKIE_NAME, issue_session_token('admin@test.com'))
        yield test_client
    set_llm(None)
