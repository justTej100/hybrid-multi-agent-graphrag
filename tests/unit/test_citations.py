from __future__ import annotations

from citations import (
    citation_links,
    extract_page_citations,
    is_citation_only,
    linkify_citations,
    resolve_document_id,
    strip_citation_tags,
)


def test_linkify_page_citations():
    sources = [
        {
            'document_id': 'doc-a',
            'document_title': 'Algebra',
            'page_number': 12,
            'text': 'sample',
        },
    ]
    linked = linkify_citations('See [p12] for details.', sources)
    assert '[p12](/pdf/doc-a?page=12)' in linked


def test_resolve_document_id_by_page():
    sources = [
        {'document_id': 'doc-a', 'page_number': 3},
        {'document_id': 'doc-b', 'page_number': 5},
    ]
    assert resolve_document_id(3, sources) == 'doc-a'


def test_citation_links_page_only():
    sources = [
        {
            'document_id': 'doc-1',
            'document_title': 'Linear Algebra',
            'page_number': 1,
            'text': 'vectors',
        }
    ]
    links = citation_links([1], sources)
    assert links[0]['document_title'] == 'Linear Algebra'
    assert links[0]['href'] == '/pdf/doc-1?page=1'
    assert links[0]['label'] == 'Linear Algebra · p1'


def test_extract_page_citations_dedupes():
    assert extract_page_citations('[p1] text [p1] [p2]') == [1, 2]


def test_is_citation_only_detects_page_tags_without_prose():
    assert is_citation_only('[p1] [p2] [p3]')
    assert is_citation_only('References: [p1] [p2]')


def test_is_citation_only_detects_legacy_sentence_tags():
    assert is_citation_only('[p1:s3] [p1:s6] [p1:s12]')


def test_is_citation_only_accepts_real_answer():
    text = (
        'This course covers algorithms, data structures, and systems topics including '
        'memory management and process scheduling across several units. See [p5] for the outline.'
    )
    assert not is_citation_only(text)


def test_strip_citation_tags_page_and_legacy():
    assert strip_citation_tags('Hello [p1] world [p2:s3]') == 'Hello world'
