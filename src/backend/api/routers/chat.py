from __future__ import annotations

"""Chat / study endpoints: /chat and /search (alias)."""

from fastapi import APIRouter, Depends, HTTPException, Request

from agents.Pipeline import ResearchPipeline
from ai.clients import GeminiAPIError
from mail.gmail import EmailNotConfiguredError, send_flashcards_email
from router.auth import get_session_email, is_admin_email, require_session
from router.rate_limit import check_and_record_chat
from schemas import ChatRequest, EvalResponse, StudyResponse

router = APIRouter(tags=['Study'])

pipeline = ResearchPipeline()


@router.post('/chat', response_model=StudyResponse, dependencies=[Depends(require_session)])
async def chat(request: Request, body: ChatRequest) -> StudyResponse:
    user_messages = [m for m in body.messages if m.role == 'user']
    if not user_messages:
        raise HTTPException(status_code=400, detail='At least one user message is required.')

    email = get_session_email(request) or ''
    await check_and_record_chat(email, is_admin=is_admin_email(email))

    query = user_messages[-1].content
    history = [{'role': m.role, 'content': m.content} for m in body.messages[:-1]] or None
    scope = body.scope.model_dump()

    try:
        result = await pipeline.run(
            query=query,
            query_type='study',
            conversation_history=history,
            scope=scope,
            mode=body.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeminiAPIError as exc:
        status_code = exc.status_code if exc.status_code in {429, 503, 502} else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    study_response = StudyResponse(
        query=result.query,
        type=result.query_type,
        brief=result.brief,
        eval=EvalResponse(**vars(result.eval)),
        sources=result.sources,
        meta=result.meta,
        structured=result.structured,
    )
    await _maybe_email_flashcards(request, body, study_response)
    return study_response


async def _maybe_email_flashcards(request: Request, body: ChatRequest, result: StudyResponse) -> None:
    if body.mode != 'flashcards' or not body.email_flashcards:
        return
    items = (result.structured or {}).get('items', [])
    if not items:
        return
    recipient = get_session_email(request)
    if not recipient:
        return
    topic = body.messages[-1].content if body.messages else 'Study topic'
    try:
        send_flashcards_email(to_email=recipient, topic=topic, items=items, sources=result.sources)
    except (EmailNotConfiguredError, ValueError):
        return


@router.post('/search', response_model=StudyResponse, dependencies=[Depends(require_session)])
async def search(request: Request, body: ChatRequest) -> StudyResponse:
    return await chat(request, body)