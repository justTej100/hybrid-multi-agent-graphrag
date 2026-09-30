from __future__ import annotations

"""Chat / study endpoints: /chat and /search (alias)."""

from fastapi import APIRouter, Depends, HTTPException, Request

from agents.service import LLMError, run_study
from api.routers.auth import get_session_email, is_admin_email, require_admin, require_session
from api.routers.rate_limit import check_and_record_chat
from api.schemas import ChatRequest, EvalResponse, StudyResponse
from db.client import (
    append_study_message,
    create_study_session,
    get_study_session,
    list_study_sessions,
)
from mail.gmail import EmailNotConfiguredError, send_flashcards_email

router = APIRouter(tags=['Study'])


@router.post('/chat', response_model=StudyResponse, dependencies=[Depends(require_session)])
async def chat(request: Request, body: ChatRequest) -> StudyResponse:
    user_messages = [message for message in body.messages if message.role == 'user']
    if not user_messages:
        raise HTTPException(status_code=400, detail='At least one user message is required.')

    email = get_session_email(request) or ''
    await check_and_record_chat(email, is_admin=is_admin_email(email))

    query = user_messages[-1].content
    history = [{'role': message.role, 'content': message.content} for message in body.messages[:-1]] or None
    scope = body.scope.model_dump()

    try:
        result = await run_study(query=query, history=history, scope=scope, mode=body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    meta = dict(result.meta)
    if is_admin_email(email):
        session_id = await _save_admin_session(email, body, query, scope, result)
        meta['session_id'] = session_id

    study_response = StudyResponse(
        query=result.query,
        type=result.query_type,
        brief=result.brief,
        eval=EvalResponse(**result.eval),
        sources=result.sources,
        meta=meta,
        structured=result.structured,
    )
    await _maybe_email_flashcards(request, body, study_response)
    return study_response


async def _save_admin_session(email: str, body: ChatRequest, query: str, scope: dict, result) -> str:
    session_id = body.session_id
    if session_id:
        existing = await get_study_session(session_id, email)
        if existing is None:
            raise HTTPException(status_code=404, detail='Session not found.')
    else:
        session_id = await create_study_session(email, query, body.mode, scope)
    await append_study_message(session_id, 'user', query)
    await append_study_message(
        session_id,
        'assistant',
        result.brief,
        sources=result.sources,
        structured=result.structured,
    )
    return session_id


@router.get('/sessions', dependencies=[Depends(require_admin)])
async def sessions(request: Request) -> list[dict]:
    email = get_session_email(request) or ''
    return await list_study_sessions(email)


@router.get('/sessions/{session_id}', dependencies=[Depends(require_admin)])
async def session_detail(session_id: str, request: Request) -> dict:
    email = get_session_email(request) or ''
    session = await get_study_session(session_id, email)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found.')
    return session


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
