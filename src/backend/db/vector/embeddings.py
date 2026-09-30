from __future__ import annotations

from google import genai
from google.genai import types

VECTOR_SIZE = 3072


class GeminiEmbedder:
    """Gemini embeddings forced to 3072 dimensions so they fit vector_chunks."""

    def __init__(
        self,
        api_key: str,
        model: str = 'gemini-embedding-001',
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self._config = types.EmbedContentConfig(output_dimensionality=VECTOR_SIZE)

    def embed_text(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=self._config,
        )
        return list(response.embeddings[0].values)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.models.embed_content(
            model=self.model,
            contents=texts,
            config=self._config,
        )
        return [list(embedding.values) for embedding in response.embeddings]
