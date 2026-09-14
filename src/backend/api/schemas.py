from __future__ import annotations

"""Shared Pydantic request/response models used across router modules."""

from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str


class Scope(BaseModel):
    type: Literal['document', 'library'] = 'library'
    document_id: str | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    mode: Literal['chat', 'quiz', 'flashcards', 'summary'] = 'chat'
    scope: Scope = Scope()
    email_flashcards: bool = False


class FlashcardEmailRequest(BaseModel):
    topic: str
    items: list[dict]
    sources: list[dict] = []


class FlashcardSubscribeRequest(BaseModel):
    document_id: str


class FlashcardOpenRequest(BaseModel):
    enabled: bool


class FlashcardBroadcastRequest(BaseModel):
    document_id: str
    topic: str
    items: list[dict]
    sources: list[dict] = []


class BulkDeleteRequest(BaseModel):
    document_ids: list[str]


class EvalResponse(BaseModel):
    passed: bool
    score: float
    claims_checked: int
    claims_grounded: int
    ungrounded_claims: list[str]
    explanation: str
    citation_errors: list[str]


class StudyResponse(BaseModel):
    query: str
    type: str
    brief: str
    eval: EvalResponse
    sources: list[dict]
    meta: dict
    structured: dict | None = None