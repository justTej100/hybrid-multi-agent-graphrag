from __future__ import annotations

"""Read-only view of the knowledge graph for signed-in users.

A browser navigation asks for HTML and receives the SPA. The app fetches the
same path and receives JSON.
"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from api.routers.auth import get_session_email
from db.client import get_kg_adapter

router = APIRouter(tags=['Graph'])

FRONTEND_DIST = Path(__file__).resolve().parents[3] / 'frontend' / 'dist'


def _wants_html(request: Request) -> bool:
    accept = request.headers.get('accept', '')
    return accept.startswith('text/html')


def _load_graph() -> dict:
    adapter = get_kg_adapter()
    if adapter is None:
        return {'enabled': False, 'nodes': [], 'edges': []}
    graph = adapter.list_graph()
    return {'enabled': True, 'nodes': graph['nodes'], 'edges': graph['edges']}


@router.get('/graph')
async def graph(request: Request):
    if _wants_html(request):
        index = FRONTEND_DIST / 'index.html'
        if not index.is_file():
            raise HTTPException(
                status_code=503,
                detail='Frontend not built. Run: cd src/frontend && npm install && npm run build',
            )
        return FileResponse(index)
    if not get_session_email(request):
        raise HTTPException(status_code=401, detail='Not authenticated.')
    try:
        return await asyncio.to_thread(_load_graph)
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Knowledge graph is unavailable.') from exc
