from __future__ import annotations

"""Process-wide settings loaded from the environment and the repo-root .env."""

import os
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


def _load_dotenv() -> None:
    """Load the repo-root .env without overriding variables already set."""
    if os.environ.get('ARGUS_SKIP_DOTENV') == '1':
        return
    from dotenv import load_dotenv

    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / '.env', override=False)


_load_dotenv()

EMBED_MODEL = 'models/gemini-embedding-001'
VECTOR_SIZE = 3072
DEFAULT_CHAT_MODEL = 'gemini-2.5-flash'

_embedder = None


def database_url() -> str:
    return os.environ.get('DATABASE_URL', '').strip()


def gemini_api_key() -> str:
    return os.environ.get('GEMINI_API_KEY', '').strip() or os.environ.get('GOOGLE_API_KEY', '').strip()


def deepseek_api_key() -> str:
    return os.environ.get('DEEPSEEK_API_KEY', '').strip()


def neo4j_settings() -> dict[str, str]:
    return {
        'uri': os.environ.get('NEO4J_URI', '').strip(),
        'username': os.environ.get('NEO4J_USERNAME', 'neo4j').strip() or 'neo4j',
        'password': os.environ.get('NEO4J_PASSWORD', '').strip(),
    }


def kg_enabled() -> bool:
    """Knowledge-graph ingestion and search run only when Neo4j and DeepSeek are configured."""
    neo4j = neo4j_settings()
    return bool(neo4j['uri'] and neo4j['password'] and deepseek_api_key())


def set_embedder(embedder) -> None:
    """Replace the process embedder (tests inject a deterministic stand-in)."""
    global _embedder
    _embedder = embedder


def get_embedder():
    """Return the shared embedder, constructing the Gemini client on first use."""
    global _embedder
    if _embedder is None:
        from db.vector.embeddings import GeminiEmbedder

        _embedder = GeminiEmbedder(api_key=gemini_api_key())
    return _embedder


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Gemini embeddings at 3072 dimensions (matches the vector_chunks column)."""
    return GoogleGenerativeAIEmbeddings(
        model=EMBED_MODEL,
        google_api_key=gemini_api_key(),
        output_dimensionality=VECTOR_SIZE,
    )


def get_chat_model(*, temperature: float = 0.4, json_mode: bool = False) -> ChatGoogleGenerativeAI:
    """Gemini chat model for tutor answers. Override the model with GEMINI_MODEL."""
    kwargs: dict = {
        'model': os.environ.get('GEMINI_MODEL', DEFAULT_CHAT_MODEL),
        'google_api_key': gemini_api_key(),
        'temperature': temperature,
    }
    if json_mode:
        kwargs['response_mime_type'] = 'application/json'
    return ChatGoogleGenerativeAI(**kwargs)
