from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from integration_services import POSTGRES_URL, postgres_or_skip


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
