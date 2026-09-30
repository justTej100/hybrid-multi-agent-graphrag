from __future__ import annotations

"""FastAPI backend for Argus — API routes + React SPA."""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import config  # noqa: F401  loads the repo-root .env
from api.routers import admin, auth, chat, documents, flashcards, graph
from db.client import init_schema, shutdown

FRONTEND_DIST = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_schema()
    yield
    await shutdown()


app = FastAPI(title='Argus Study Buddy', version='3.0.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
    allow_credentials=True,
)
app.add_middleware(SessionMiddleware, secret_key=os.environ.get('SECRET_KEY', 'dev-argus-secret'))

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(flashcards.router)
app.include_router(admin.router)
app.include_router(graph.router)


def _spa_index() -> FileResponse:
    index = FRONTEND_DIST / 'index.html'
    if not index.is_file():
        raise HTTPException(
            status_code=503,
            detail='Frontend not built. Run: cd src/frontend && npm install && npm run build',
        )
    return FileResponse(index)


@app.get('/')
async def spa_home() -> FileResponse:
    return _spa_index()


@app.get('/login')
async def spa_login() -> FileResponse:
    return _spa_index()


@app.get('/study')
async def spa_study() -> FileResponse:
    return _spa_index()


@app.get('/admin')
async def spa_admin() -> FileResponse:
    return _spa_index()


@app.get('/library')
async def spa_library() -> FileResponse:
    return _spa_index()


@app.get('/quiz')
async def spa_quiz() -> FileResponse:
    return _spa_index()


@app.get('/flashcards')
async def spa_flashcards() -> FileResponse:
    return _spa_index()


@app.get('/health')
def health() -> dict:
    return {'status': 'ok', 'timestamp': time.time()}


_assets_dir = FRONTEND_DIST / 'assets'
if _assets_dir.is_dir():
    app.mount('/assets', StaticFiles(directory=_assets_dir), name='frontend_assets')
