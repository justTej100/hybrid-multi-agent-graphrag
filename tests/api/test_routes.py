from __future__ import annotations

from fastapi.testclient import TestClient

from fakes import make_pdf

VARIANCE = (
    'Variance measures the spread of data around the mean. '
    'A larger variance means the observations are more dispersed.'
)
MITO = 'Mitochondria produce energy inside a living cell and are not a statistics concept.'


def _upload(client: TestClient, title: str, text: str, description: str | None = None) -> str:
    data = {'title': title}
    if description is not None:
        data['description'] = description
    response = client.post(
        '/documents',
        files={'file': (f'{title}.pdf', make_pdf(text), 'application/pdf')},
        data=data,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['status'] == 'processing'
    assert body['job_id'].startswith('ingest-')
    return body['id']


def test_health(client: TestClient) -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_chat_requires_session(client: TestClient) -> None:
    response = client.post(
        '/chat',
        json={'messages': [{'role': 'user', 'content': 'hello'}], 'mode': 'chat', 'scope': {'type': 'library'}},
    )
    assert response.status_code == 401


def test_chat_rejects_empty_user_message(authenticated_client: TestClient) -> None:
    response = authenticated_client.post(
        '/chat',
        json={'messages': [{'role': 'assistant', 'content': 'hi'}], 'mode': 'chat', 'scope': {'type': 'library'}},
    )
    assert response.status_code == 400


def test_logout_clears_session(authenticated_client: TestClient) -> None:
    chat = {
        'messages': [{'role': 'user', 'content': 'What is variance?'}],
        'mode': 'chat',
        'scope': {'type': 'library'},
    }
    assert authenticated_client.post('/chat', json=chat).status_code == 200
    logout = authenticated_client.get('/logout', follow_redirects=False)
    assert logout.status_code == 302
    assert 'Max-Age=0' in logout.headers.get('set-cookie', '')
    authenticated_client.cookies.clear()
    assert authenticated_client.post('/chat', json=chat).status_code == 401


def test_upload_ingests_and_serves_file(authenticated_client: TestClient) -> None:
    payload = make_pdf(VARIANCE)
    upload = authenticated_client.post(
        '/documents',
        files={'file': ('book.pdf', payload, 'application/pdf')},
        data={'title': 'Statistics', 'description': 'Spread'},
    )
    assert upload.status_code == 200
    document_id = upload.json()['id']

    status = authenticated_client.get(f'/documents/{document_id}/status')
    assert status.status_code == 200
    body = status.json()
    assert body['status'] == 'ready'
    assert body['total_pages'] == 1
    assert body['has_scan_warning'] is False

    listed = authenticated_client.get('/documents')
    assert listed.status_code == 200
    match = next(item for item in listed.json() if item['id'] == document_id)
    assert match['title'] == 'Statistics'
    assert match['description'] == 'Spread'

    downloaded = authenticated_client.get(f'/documents/{document_id}/file')
    assert downloaded.status_code == 200
    assert downloaded.content == payload
    assert downloaded.headers['content-type'] == 'application/pdf'


def test_rejects_non_pdf(authenticated_client: TestClient) -> None:
    response = authenticated_client.post(
        '/documents',
        files={'file': ('notes.txt', b'hello', 'text/plain')},
        data={'title': 'Notes'},
    )
    assert response.status_code == 400


def test_guest_cannot_upload_or_delete(guest_client: TestClient) -> None:
    upload = guest_client.post(
        '/documents',
        files={'file': ('book.pdf', make_pdf(VARIANCE), 'application/pdf')},
        data={'title': 'Nope'},
    )
    assert upload.status_code == 403
    assert guest_client.delete('/documents/missing').status_code == 403
    assert guest_client.post('/documents/bulk-delete', json={'document_ids': ['x']}).status_code == 403
    assert guest_client.patch('/documents/missing/flashcards-open', json={'enabled': True}).status_code == 403


def test_bulk_delete_and_missing_document(authenticated_client: TestClient) -> None:
    first = _upload(authenticated_client, 'Book A', VARIANCE, 'math')
    second = _upload(authenticated_client, 'Book B', MITO, 'bio')
    assert authenticated_client.get('/documents/does-not-exist/status').status_code == 404

    removed = authenticated_client.delete(f'/documents/{first}')
    assert removed.status_code == 200
    assert authenticated_client.get(f'/documents/{first}/status').status_code == 404

    bulk = authenticated_client.post('/documents/bulk-delete', json={'document_ids': [second, 'missing']})
    assert bulk.status_code == 200
    assert bulk.json()['deleted'] == 1
    assert authenticated_client.get('/documents').json() == []


def test_chat_modes_use_uploaded_pages(authenticated_client: TestClient) -> None:
    document_id = _upload(authenticated_client, 'Statistics', VARIANCE)
    chat = authenticated_client.post(
        '/chat',
        json={
            'messages': [
                {'role': 'user', 'content': 'Earlier we discussed spread.'},
                {'role': 'assistant', 'content': 'Go on.'},
                {'role': 'user', 'content': 'What is variance?'},
            ],
            'mode': 'chat',
            'scope': {'type': 'document', 'document_id': document_id},
        },
    )
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body['type'] == 'chat'
    assert body['eval']['passed'] is True
    assert body['eval']['citation_errors'] == []
    assert '[p1]' in body['brief']
    assert body['sources']
    assert all(source['document_id'] == document_id for source in body['sources'])
    assert body['sources'][0]['page_number'] == 1

    search = authenticated_client.post(
        '/search',
        json={
            'messages': [{'role': 'user', 'content': 'What is variance?'}],
            'mode': 'summary',
            'scope': {'type': 'library'},
        },
    )
    assert search.status_code == 200
    assert search.json()['type'] == 'summary'

    quiz = authenticated_client.post(
        '/chat',
        json={
            'messages': [{'role': 'user', 'content': 'Quiz me on variance'}],
            'mode': 'quiz',
            'scope': {'type': 'library'},
        },
    )
    assert quiz.status_code == 200
    assert len(quiz.json()['structured']['questions']) == 3

    cards = authenticated_client.post(
        '/chat',
        json={
            'messages': [{'role': 'user', 'content': 'Make flashcards'}],
            'mode': 'flashcards',
            'scope': {'type': 'library'},
        },
    )
    assert cards.status_code == 200
    assert cards.json()['structured']['items'][0]['front'] == 'What is variance?'


def test_guest_chat_is_rate_limited(guest_client: TestClient) -> None:
    payload = {
        'messages': [{'role': 'user', 'content': 'What is variance?'}],
        'mode': 'chat',
        'scope': {'type': 'library'},
    }
    assert guest_client.post('/chat', json=payload).status_code == 200
    second = guest_client.post('/chat', json=payload)
    assert second.status_code == 429
    assert second.json()['detail']['retry_after_seconds'] > 0


def test_me_reports_role(client: TestClient) -> None:
    from api.routers.auth import COOKIE_NAME, issue_session_token

    client.cookies.set(COOKIE_NAME, issue_session_token('admin@test.com'))
    admin = client.get('/me')
    assert admin.status_code == 200
    assert admin.json()['is_admin'] is True
    assert admin.json()['chat']['unlimited'] is True

    client.cookies.set(COOKIE_NAME, issue_session_token('guest@example.com'))
    guest = client.get('/me')
    assert guest.status_code == 200
    assert guest.json()['is_admin'] is False
    assert guest.json()['chat']['unlimited'] is False


def test_flashcard_subscribe_and_email(client: TestClient, monkeypatch) -> None:
    from api.routers.auth import COOKIE_NAME, issue_session_token

    sent: list[tuple] = []

    class _SMTP:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, *args, **kwargs):
            del args, kwargs

        def sendmail(self, sender, recipients, message):
            sent.append((sender, recipients, message))

    monkeypatch.setenv('GMAIL_USER', 'bot@example.com')
    monkeypatch.setenv('GMAIL_APP_PASSWORD', 'app-password')
    import mail.gmail as gmail

    monkeypatch.setattr(gmail.smtplib, 'SMTP_SSL', _SMTP)

    client.cookies.set(COOKIE_NAME, issue_session_token('admin@test.com'))
    document_id = _upload(client, 'Statistics', VARIANCE, 'spread')

    client.cookies.set(COOKIE_NAME, issue_session_token('guest@example.com'))
    closed = client.post('/flashcards/subscribe', json={'document_id': document_id})
    assert closed.status_code == 400

    client.cookies.set(COOKIE_NAME, issue_session_token('admin@test.com'))
    opened = client.patch(f'/documents/{document_id}/flashcards-open', json={'enabled': True})
    assert opened.status_code == 200
    assert opened.json()['flashcards_open'] is True

    client.cookies.set(COOKIE_NAME, issue_session_token('guest@example.com'))
    subscribed = client.post('/flashcards/subscribe', json={'document_id': document_id})
    assert subscribed.status_code == 200
    offers = client.get('/flashcards/offers')
    assert offers.status_code == 200
    assert offers.json()[0]['subscribed'] is True
    assert offers.json()[0]['subscriber_count'] == 1

    mailed = client.post(
        '/flashcards/email',
        json={
            'topic': 'Variance',
            'items': [{'front': 'Q', 'back': 'A', 'citations': ['[p1]']}],
            'sources': [{'document_id': document_id, 'page_number': 1, 'text': VARIANCE}],
        },
    )
    assert mailed.status_code == 200
    assert mailed.json()['count'] == 1
    assert sent and sent[0][1] == ['guest@example.com']

    client.post('/flashcards/unsubscribe', json={'document_id': document_id})
    assert client.get('/flashcards/offers').json()[0]['subscribed'] is False

    client.cookies.set(COOKIE_NAME, issue_session_token('admin@test.com'))
    empty = client.post(
        '/flashcards/broadcast',
        json={'document_id': document_id, 'topic': 'Variance', 'items': [{'front': 'Q', 'back': 'A'}], 'sources': []},
    )
    assert empty.status_code == 200
    assert empty.json()['sent'] == 0

    client.cookies.set(COOKIE_NAME, issue_session_token('guest@example.com'))
    client.post('/flashcards/subscribe', json={'document_id': document_id})
    client.cookies.set(COOKIE_NAME, issue_session_token('admin@test.com'))
    broadcast = client.post(
        '/flashcards/broadcast',
        json={
            'topic': 'Variance',
            'document_id': document_id,
            'items': [{'front': 'Q', 'back': 'A spread', 'citations': ['[p1]']}],
            'sources': [{'document_id': document_id, 'page_number': 1, 'text': VARIANCE}],
        },
    )
    assert broadcast.status_code == 200
    assert broadcast.json()['sent'] == 1


def test_flashcard_email_requires_configuration(authenticated_client: TestClient) -> None:
    response = authenticated_client.post(
        '/flashcards/email',
        json={'topic': 'Variance', 'items': [{'front': 'Q', 'back': 'A'}], 'sources': []},
    )
    assert response.status_code == 503


def test_admin_stats_and_chunks(client: TestClient) -> None:
    from api.routers.auth import COOKIE_NAME, issue_session_token

    client.cookies.set(COOKIE_NAME, issue_session_token('guest@example.com'))
    assert client.get('/admin/stats').status_code == 403

    client.cookies.set(COOKIE_NAME, issue_session_token('admin@test.com'))
    document_id = _upload(client, 'Statistics', VARIANCE)
    stats = client.get('/admin/stats')
    assert stats.status_code == 200
    body = stats.json()
    assert body['document_count'] == 1
    assert body['total_vectors'] >= 1
    assert body['documents'][0]['chunk_count'] >= 1

    chunks = client.get(f'/admin/documents/{document_id}/chunks')
    assert chunks.status_code == 200
    assert 'spread' in chunks.json()['chunks'][0]['text'].lower() or 'variance' in chunks.json()['chunks'][0]['text'].lower()

    config = client.get('/admin/config')
    assert config.status_code == 200
    assert 'supabaseTableUrl' in config.json()


def test_only_admin_chats_are_saved(client: TestClient) -> None:
    from api.routers.auth import COOKIE_NAME, issue_session_token

    payload = {
        'messages': [{'role': 'user', 'content': 'What is variance?'}],
        'mode': 'chat',
        'scope': {'type': 'library'},
    }
    client.cookies.set(COOKIE_NAME, issue_session_token('admin@test.com'))
    first = client.post('/chat', json=payload)
    assert first.status_code == 200, first.text
    session_id = first.json()['meta']['session_id']

    listed = client.get('/sessions')
    assert listed.status_code == 200
    assert [row['id'] for row in listed.json()] == [session_id]
    detail = client.get(f'/sessions/{session_id}')
    assert detail.status_code == 200
    messages = detail.json()['messages']
    assert [message['role'] for message in messages] == ['user', 'assistant']
    assert messages[0]['content'] == 'What is variance?'

    follow = client.post(
        '/chat',
        json={
            **payload,
            'session_id': session_id,
            'messages': [{'role': 'user', 'content': 'And the mean?'}],
        },
    )
    assert follow.status_code == 200
    assert follow.json()['meta']['session_id'] == session_id
    assert len(client.get(f'/sessions/{session_id}').json()['messages']) == 4

    client.cookies.set(COOKIE_NAME, issue_session_token('guest@example.com'))
    assert client.get('/sessions').status_code == 403
    guest = client.post('/chat', json=payload)
    assert guest.status_code == 200
    assert 'session_id' not in guest.json()['meta']

    client.cookies.set(COOKIE_NAME, issue_session_token('admin@test.com'))
    assert len(client.get('/sessions').json()) == 1


def test_graph_is_off_without_neo4j(authenticated_client: TestClient) -> None:
    response = authenticated_client.get('/graph', headers={'Accept': 'application/json'})
    assert response.status_code == 200
    body = response.json()
    assert body == {'enabled': False, 'nodes': [], 'edges': []}
