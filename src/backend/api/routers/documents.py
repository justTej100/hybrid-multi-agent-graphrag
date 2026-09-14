from __future__ import annotations

"""Document upload, listing, status, deletion, and file retrieval."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response as FastAPIResponse

from db.client import create_document, delete_document, get_document, list_documents, update_document_status
from db.subscriptions import set_flashcards_open
from jobs import schedule_ingestion
from router.auth import require_admin, require_session
from schemas import BulkDeleteRequest, FlashcardOpenRequest
from storage import delete_pdf, download_pdf, upload_pdf

router = APIRouter(prefix='/documents', tags=['Documents'])


@router.get('', dependencies=[Depends(require_session)])
async def documents() -> list[dict]:
    return await list_documents()


@router.post('', dependencies=[Depends(require_admin)])
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str | None = Form(None),
) -> dict:
    filename = file.filename or ''
    if file.content_type not in {'application/pdf', 'application/octet-stream'} and not filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF uploads are supported.')

    payload = await file.read()
    document_id = await create_document(
        title=title,
        description=description or None,
        status='processing',
        total_pages=0,
        storage_path='',
    )
    storage_path = upload_pdf(document_id, filename or f'{document_id}.pdf', payload)
    await update_document_status(document_id, status='processing', storage_path=storage_path)
    job_id = schedule_ingestion(document_id, storage_path)
    return {'id': document_id, 'status': 'processing', 'job_id': job_id}


@router.get('/{document_id}/status', dependencies=[Depends(require_session)])
async def document_status(document_id: str) -> dict:
    document = await get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail='Document not found.')
    return {
        'id': document['id'],
        'status': document['status'],
        'total_pages': document.get('total_pages'),
        'has_scan_warning': document.get('has_scan_warning', False),
        'error_message': document.get('error_message'),
    }


@router.delete('/{document_id}', dependencies=[Depends(require_admin)])
async def remove_document(document_id: str) -> dict:
    document = await get_document(document_id)
    if document:
        delete_pdf(document.get('storage_path') or '')
    await delete_document(document_id)
    return {'ok': True}


@router.post('/bulk-delete', dependencies=[Depends(require_admin)])
async def bulk_remove_documents(body: BulkDeleteRequest) -> dict:
    deleted: list[str] = []
    for document_id in body.document_ids:
        document = await get_document(document_id)
        if not document:
            continue
        delete_pdf(document.get('storage_path') or '')
        await delete_document(document_id)
        deleted.append(document_id)
    return {'deleted': len(deleted), 'ids': deleted}


@router.get('/{document_id}/file', dependencies=[Depends(require_session)])
async def get_document_file(document_id: str) -> FastAPIResponse:
    from storage import StorageError

    document = await get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail='Document not found.')
    storage_path = document.get('storage_path') or ''
    if not storage_path:
        raise HTTPException(status_code=404, detail='PDF has not been stored yet.')
    try:
        blob = download_pdf(storage_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail='PDF file missing from storage. Set STORAGE_BACKEND=local or configure Supabase keys.',
        ) from None
    except StorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return FastAPIResponse(content=blob, media_type='application/pdf')


@router.patch('/{document_id}/flashcards-open', dependencies=[Depends(require_admin)])
async def document_flashcards_open(document_id: str, body: FlashcardOpenRequest) -> dict:
    document = await set_flashcards_open(document_id, body.enabled)
    if not document:
        raise HTTPException(status_code=404, detail='Document not found.')
    return {
        'id': document['id'],
        'flashcards_open': bool(document.get('flashcards_open')),
        'title': document.get('title'),
    }