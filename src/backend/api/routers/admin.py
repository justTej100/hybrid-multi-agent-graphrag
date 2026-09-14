from __future__ import annotations

"""Admin dashboard endpoints: config, stats, chunk inspection."""

from fastapi import APIRouter, Depends, HTTPException

from db.client import get_document, list_documents
from router.auth import require_admin
from storage import supabase_dashboard_urls

router = APIRouter(prefix='/admin', tags=['Admin'], dependencies=[Depends(require_admin)])


@router.get('/config')
async def admin_config() -> dict:
    urls = supabase_dashboard_urls()
    return {
        'supabaseTableUrl': urls.get('tableEditorUrl'),
        'storageUrl': urls.get('storageUrl'),
    }


@router.get('/stats')
async def admin_stats() -> dict:
    from ai.langchain_store import count_vectors, count_vectors_for_document

    docs = await list_documents()
    total_vectors = await count_vectors()
    per_doc = []
    for doc in docs:
        per_doc.append(
            {
                'id': doc['id'],
                'title': doc['title'],
                'description': doc.get('description'),
                'status': doc['status'],
                'total_pages': doc.get('total_pages'),
                'storage_path': doc.get('storage_path'),
                'chunk_count': await count_vectors_for_document(doc['id']),
            }
        )
    return {
        'document_count': len(docs),
        'total_vectors': total_vectors,
        'documents': per_doc,
    }


@router.get('/documents/{document_id}/chunks')
async def admin_document_chunks(document_id: str, limit: int = 5) -> dict:
    from ai.langchain_store import sample_vectors

    document = await get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail='Document not found.')
    chunks = await sample_vectors(document_id, limit=min(limit, 20))
    return {'document_id': document_id, 'title': document['title'], 'chunks': chunks}