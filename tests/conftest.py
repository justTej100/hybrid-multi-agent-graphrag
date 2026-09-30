from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Keep developer .env values from pointing the fast suite at a real database.
os.environ['ARGUS_SKIP_DOTENV'] = '1'
os.environ['DATABASE_URL'] = ''
os.environ['NEO4J_URI'] = ''
os.environ['NEO4J_PASSWORD'] = ''
os.environ['DEEPSEEK_API_KEY'] = ''
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('ADMIN_EMAIL', 'admin@test.com')

_TESTS = Path(__file__).resolve().parent
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))


def _session(client: TestClient, email: str) -> TestClient:
    from api.routers.auth import COOKIE_NAME, issue_session_token

    client.cookies.set(COOKIE_NAME, issue_session_token(email))
    return client


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('ADMIN_EMAIL', 'admin@test.com')
    monkeypatch.setenv('DATABASE_URL', '')
    monkeypatch.setenv('NEO4J_URI', '')
    monkeypatch.setenv('NEO4J_PASSWORD', '')
    monkeypatch.setenv('DEEPSEEK_API_KEY', '')
    monkeypatch.setenv('STORAGE_BACKEND', 'local')
    monkeypatch.setenv('ARGUS_INGEST_INLINE', '1')
    monkeypatch.setenv('GUEST_CHAT_COOLDOWN_SECONDS', '300')
    monkeypatch.setenv('GUEST_CHAT_DAILY_LIMIT', '10')
    monkeypatch.setenv('GMAIL_USER', '')
    monkeypatch.setenv('GMAIL_APP_PASSWORD', '')

    import storage
    from agents.service import set_llm
    from api.main import app
    from api.routers.rate_limit import reset_memory_usage
    from db.client import reset_memory
    from db.subscriptions import reset_memory_subscriptions
    from fakes import FakeChatModel

    monkeypatch.setattr(storage, 'LOCAL_UPLOAD_DIR', tmp_path)
    reset_memory()
    reset_memory_subscriptions()
    reset_memory_usage()
    set_llm(FakeChatModel())

    with TestClient(app) as test_client:
        yield test_client
    set_llm(None)


@pytest.fixture
def authenticated_client(client: TestClient) -> TestClient:
    return _session(client, 'admin@test.com')


@pytest.fixture
def guest_client(client: TestClient) -> TestClient:
    return _session(client, 'guest@example.com')
