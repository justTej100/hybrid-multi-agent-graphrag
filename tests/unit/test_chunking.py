from __future__ import annotations

from db.vector.chunking import chunk_pages
from jobs import looks_like_scan


def test_chunk_pages_keeps_page_and_ids() -> None:
    pages = [
        {'document_id': 'doc-1', 'page_number': 1, 'text': 'Variance is the spread of data.'},
        {'document_id': 'doc-1', 'page_number': 2, 'text': 'The mean is a measure of center.'},
    ]
    chunks = chunk_pages(pages)
    assert chunks
    assert chunks[0]['page_number'] == 1
    assert chunks[0]['document_id'] == 'doc-1'
    assert chunks[0]['chunk_id'].startswith('doc-1_p1_')
    assert 'Variance' in chunks[0]['content']
    assert {chunk['page_number'] for chunk in chunks} == {1, 2}


def test_looks_like_scan_flags_empty_pages() -> None:
    pages = [
        {'page_number': 1, 'text': 'A short page.'},
        {'page_number': 2, 'text': ''},
    ]
    assert looks_like_scan(pages) is True
    assert looks_like_scan([{'page_number': 1, 'text': 'Variance measures the spread of data around the mean.'}]) is False
