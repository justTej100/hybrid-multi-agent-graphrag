from __future__ import annotations

"""Flashcard email delivery + subscription management."""

from fastapi import APIRouter, Depends, HTTPException, Request

from db.client import get_document
from db.subscriptions import (
    list_flashcard_offers,
    list_subscriber_emails,
    subscribe as subscribe_flashcards,
    unsubscribe as unsubscribe_flashcards,
)
from mail.gmail import EmailNotConfiguredError, send_flashcards_email
from router.auth import get_session_email, require_admin, require_session
from schemas import FlashcardBroadcastRequest, FlashcardEmailRequest, FlashcardSubscribeRequest

router = APIRouter(prefix='/flashcards', tags=['Flashcards'])


@router.post('/email', tags=['Study'], dependencies=[Depends(require_session)])
async def email_flashcards(request: Request, body: FlashcardEmailRequest) -> dict:
    recipient = get_session_email(request)
    if not recipient:
        raise HTTPException(status_code=401, detail='Login required.')
    if not body.items:
        raise HTTPException(status_code=400, detail='No flashcards to email.')
    try:
        send_flashcards_email(
            to_email=recipient,
            topic=body.topic,
            items=body.items,
            sources=body.sources,
        )
    except EmailNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'ok': True, 'to': recipient, 'count': len(body.items)}


@router.get('/offers', dependencies=[Depends(require_session)])
async def flashcard_offers(request: Request) -> list[dict]:
    email = get_session_email(request)
    return await list_flashcard_offers(email)


@router.post('/subscribe', dependencies=[Depends(require_session)])
async def flashcard_subscribe(request: Request, body: FlashcardSubscribeRequest) -> dict:
    email = get_session_email(request)
    if not email:
        raise HTTPException(status_code=401, detail='Login required.')
    try:
        await subscribe_flashcards(email, body.document_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'ok': True, 'document_id': body.document_id, 'subscribed': True}


@router.post('/unsubscribe', dependencies=[Depends(require_session)])
async def flashcard_unsubscribe(request: Request, body: FlashcardSubscribeRequest) -> dict:
    email = get_session_email(request)
    if not email:
        raise HTTPException(status_code=401, detail='Login required.')
    await unsubscribe_flashcards(email, body.document_id)
    return {'ok': True, 'document_id': body.document_id, 'subscribed': False}


@router.post('/broadcast', dependencies=[Depends(require_admin)])
async def flashcard_broadcast(body: FlashcardBroadcastRequest) -> dict:
    document = await get_document(body.document_id)
    if not document:
        raise HTTPException(status_code=404, detail='Document not found.')
    if not body.items:
        raise HTTPException(status_code=400, detail='No flashcards to email.')
    recipients = await list_subscriber_emails(body.document_id)
    if not recipients:
        return {'ok': True, 'sent': 0, 'failed': 0, 'recipients': []}

    sent = 0
    failed = 0
    for recipient in recipients:
        try:
            send_flashcards_email(
                to_email=recipient,
                topic=body.topic,
                items=body.items,
                sources=body.sources,
            )
            sent += 1
        except EmailNotConfiguredError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception:
            failed += 1
    return {'ok': True, 'sent': sent, 'failed': failed, 'recipients': recipients}