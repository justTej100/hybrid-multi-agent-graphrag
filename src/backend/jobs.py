from __future__ import annotations

"""Background PDF ingestion: extract, chunk, embed, and optionally build the graph."""

import asyncio
import logging
import os
from pathlib import Path
from uuid import uuid4

from db.client import add_chunks, get_kg_adapter, update_document_status
from db.pdf import extract_pages
from db.vector.chunking import chunk_pages
from storage import download_pdf

logger = logging.getLogger(__name__)

_tasks: dict[str, asyncio.Task] = {}


def looks_like_scan(pages: list[dict]) -> bool:
    """True when a page has almost no extractable text (typical of a scanned PDF)."""
    if not pages:
        return False
    return any(len((page.get('text') or '').strip()) < 20 for page in pages)


async def _ingest(document_id: str, storage_path: str) -> None:
    temp_path: str | None = None
    try:
        payload = await asyncio.to_thread(download_pdf, storage_path)
        temp_dir = Path(os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp')
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / f'argus-{document_id}.pdf'
        await asyncio.to_thread(temp_file.write_bytes, payload)
        temp_path = str(temp_file)

        pages = await asyncio.to_thread(extract_pages, temp_path, document_id)
        if not pages:
            raise ValueError('PDF has no pages.')

        warning = looks_like_scan(pages)
        chunks = chunk_pages(pages)
        await add_chunks(document_id, chunks)

        kg = get_kg_adapter()
        if kg is not None:
            for page in pages:
                text = (page.get('text') or '').strip()
                if not text:
                    continue
                await asyncio.to_thread(
                    kg.extract_and_store,
                    text,
                    document_id,
                    int(page['page_number']),
                )

        await update_document_status(
            document_id,
            status='ready',
            total_pages=len(pages),
            has_scan_warning=warning,
        )
    except Exception as exc:
        logger.exception('Ingestion failed for %s', document_id)
        try:
            await update_document_status(document_id, status='error', error_message=str(exc)[:500])
        except Exception:
            logger.exception('Could not record ingestion failure for %s', document_id)
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def _inline_ingestion() -> bool:
    return os.environ.get('ARGUS_INGEST_INLINE', '').strip().lower() in {'1', 'true', 'yes'}


async def schedule_ingestion(document_id: str, storage_path: str) -> str:
    """Start ingestion. Tests set ARGUS_INGEST_INLINE=1 to finish before the response."""
    job_id = f'ingest-{uuid4()}'
    task = asyncio.get_running_loop().create_task(_ingest(document_id, storage_path))
    _tasks[job_id] = task
    if _inline_ingestion():
        await task
    return job_id


async def wait_for_jobs() -> None:
    """Block until every scheduled ingestion task has finished."""
    pending = [task for task in _tasks.values() if not task.done()]
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
