from __future__ import annotations

"""Misc/health endpoints."""

import time

from fastapi import APIRouter

router = APIRouter(tags=['Meta'])


@router.get('/health')
def health() -> dict:
    return {'status': 'ok', 'timestamp': time.time()}