# src/backend/db/vector/embeddings.py

from __future__ import annotations

from google import genai


class GeminiEmbedder:

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def embed_text(self, text: str) -> list[float]:

        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
        )

        return response.embeddings[0].values

    def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        response = self.client.models.embed_content(
            model=self.model,
            contents=texts,
        )

        return [
            embedding.values
            for embedding in response.embeddings
        ]