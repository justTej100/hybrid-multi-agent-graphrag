from __future__ import annotations

from db.vector.embeddings import VECTOR_SIZE, GeminiEmbedder


def test_embedder_requests_3072_dimensions(monkeypatch) -> None:
    captured: dict = {}

    class _Embedding:
        values = [0.0, 1.0]

    class _Response:
        embeddings = [_Embedding()]

    class _Models:
        def embed_content(self, **kwargs):
            captured.update(kwargs)
            return _Response()

    class _Client:
        def __init__(self, api_key: str):
            self.models = _Models()

    monkeypatch.setattr('db.vector.embeddings.genai.Client', _Client)
    embedder = GeminiEmbedder(api_key='test-key')
    assert embedder.embed_text('variance') == [0.0, 1.0]
    assert captured['model'] == 'gemini-embedding-001'
    assert captured['config'].output_dimensionality == VECTOR_SIZE == 3072
