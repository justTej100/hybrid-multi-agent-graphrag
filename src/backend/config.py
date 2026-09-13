from __future__ import annotations

import dotenv
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI



settings = dotenv.load_dotenv()


"""Gemini embedding model for LangChain PGVectorStore.

Uses GoogleGenerativeAIEmbeddings with output_dimensionality=3072 to match
gemini-embedding-001. Reads GEMINI_API_KEY or GOOGLE_API_KEY from the environment.
"""



EMBED_MODEL = 'models/gemini-embedding-001'
VECTOR_SIZE = 3072


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Gemini embeddings at 3072 dimensions (matches existing schema)."""
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '')
    return GoogleGenerativeAIEmbeddings(
        model=EMBED_MODEL,
        google_api_key=api_key,
        output_dimensionality=VECTOR_SIZE,
    )



"""Gemini chat model wrapper for LangChain LCEL chains.

Default model: gemini-2.5-flash (override with GEMINI_MODEL). Set json_mode=True
for quiz / flashcard / summary structured outputs.
"""

import os

from langchain_google_genai import 

DEFAULT_CHAT_MODEL = 'gemini-2.5-flash'


def get_chat_model(*, temperature: float = 0.4, json_mode: bool = False) -> ChatGoogleGenerativeAI:
    """Gemini chat model for tutor answers."""
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '')
    kwargs: dict = {
        'model': os.environ.get('GEMINI_MODEL', DEFAULT_CHAT_MODEL),
        'google_api_key': api_key,
        'temperature': temperature,
    }
    if json_mode:
        kwargs['response_mime_type'] = 'application/json'
    return ChatGoogleGenerativeAI(**kwargs)
