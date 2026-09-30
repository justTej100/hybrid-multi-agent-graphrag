from __future__ import annotations

"""Run the study graph and shape its final state into the API response."""

from dataclasses import dataclass

from agents.LangGraphPipeline import build_pipeline

_llm_override = None


class LLMError(Exception):
    """The study model failed. `status_code` is safe to return to the client."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def set_llm(llm) -> None:
    """Install a stand-in chat model. Pass None to use the configured provider."""
    global _llm_override
    _llm_override = llm


@dataclass
class StudyResult:
    query: str
    query_type: str
    brief: str
    eval: dict
    sources: list[dict]
    meta: dict
    structured: dict | None


def _status_from_error(exc: Exception) -> int:
    text = str(exc).lower()
    if '429' in text or 'rate limit' in text or 'resource exhausted' in text:
        return 429
    if '503' in text or 'unavailable' in text:
        return 503
    return 502


def _history_text(query: str, history: list[dict] | None) -> str:
    if not history:
        return query
    lines = [f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in history[-6:]]
    lines.append(f'user: {query}')
    return '\n'.join(lines)


async def _sources(chunks: list[dict]) -> list[dict]:
    from db.client import get_document

    titles: dict[str, str | None] = {}
    sources: list[dict] = []
    seen: set[str] = set()
    for chunk in chunks:
        chunk_id = str(chunk.get('chunk_id') or '')
        if chunk_id and chunk_id in seen:
            continue
        if chunk_id:
            seen.add(chunk_id)
        document_id = str(chunk.get('document_id') or '')
        if document_id not in titles:
            document = await get_document(document_id) if document_id else None
            titles[document_id] = document.get('title') if document else None
        sources.append(
            {
                'source_type': 'document',
                'document_id': document_id,
                'document_title': titles.get(document_id),
                'description': None,
                'page_number': int(chunk.get('page_number') or 0),
                'text': chunk.get('text') or chunk.get('content') or '',
                'similarity': chunk.get('similarity'),
            }
        )
    return sources


def _empty_eval(explanation: str) -> dict:
    return {
        'passed': False,
        'score': 0.0,
        'claims_checked': 0,
        'claims_grounded': 0,
        'ungrounded_claims': [],
        'explanation': explanation,
        'citation_errors': [],
    }


async def run_study(
    *,
    query: str,
    history: list[dict] | None,
    scope: dict | None,
    mode: str,
) -> StudyResult:
    """Invoke refine -> query -> response -> eval and map the result to StudyResponse fields."""
    llm = _llm_override if _llm_override is not None else None
    graph = build_pipeline(llm=llm)
    initial = {
        'user_input': _history_text(query, history),
        'mode': mode,
        'scope': scope or {'type': 'library'},
        'refined_query': None,
        'retrieved_chunks': None,
        'retrieved_graph_facts': None,
        'draft_response': None,
        'structured': None,
        'eval_passed': None,
        'eval_feedback': None,
        'eval_detail': None,
        'retry_count': 0,
    }
    try:
        final = await graph.ainvoke(initial)
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(str(exc) or 'The study model failed.', _status_from_error(exc)) from exc

    chunks = final.get('retrieved_chunks') or []
    return StudyResult(
        query=query,
        query_type=mode,
        brief=final.get('draft_response') or '',
        eval=final.get('eval_detail') or _empty_eval('The draft was not evaluated.'),
        sources=await _sources(chunks),
        meta={
            'retry_count': final.get('retry_count') or 0,
            'mode': mode,
            'refined_query': final.get('refined_query'),
        },
        structured=final.get('structured'),
    )
