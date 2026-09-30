from __future__ import annotations

import pytest

from agents.EvalAgent import MAX_RETRIES, route_after_eval
from agents.LangGraphPipeline import build_pipeline
from fakes import FakeChatModel


async def _chunks(query: str, scope: dict | None) -> list[dict]:
    del query, scope
    return [
        {
            'chunk_id': 'doc_p1_c0',
            'document_id': 'doc-1',
            'page_number': 1,
            'text': 'Variance measures the spread of data around the mean.',
            'similarity': 0.9,
        }
    ]


def _state(mode: str = 'chat') -> dict:
    return {
        'user_input': 'What is variance?',
        'mode': mode,
        'scope': {'type': 'library'},
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


def test_route_after_eval() -> None:
    assert route_after_eval({'eval_passed': True, 'retry_count': 3}) == 'end'
    assert route_after_eval({'eval_passed': False, 'retry_count': 1}) == 'refiner'
    assert route_after_eval({'eval_passed': False, 'retry_count': MAX_RETRIES + 1}) == 'end'


@pytest.mark.asyncio
async def test_pipeline_passes_on_first_try() -> None:
    graph = build_pipeline(llm=FakeChatModel(), retriever=_chunks)
    final = await graph.ainvoke(_state())
    assert final['eval_passed'] is True
    assert final['retry_count'] == 0
    assert final['eval_detail']['citation_errors'] == []
    assert '[p1]' in final['draft_response']
    assert final['retrieved_chunks']


@pytest.mark.asyncio
async def test_pipeline_retries_citation_only_answer() -> None:
    graph = build_pipeline(llm=FakeChatModel(bad_answers=1), retriever=_chunks)
    final = await graph.ainvoke(_state())
    assert final['eval_passed'] is True
    assert final['retry_count'] == 1
    assert 'Variance measures' in final['draft_response']


@pytest.mark.asyncio
async def test_pipeline_stops_after_max_retries() -> None:
    graph = build_pipeline(llm=FakeChatModel(bad_answers=99), retriever=_chunks)
    final = await graph.ainvoke(_state())
    assert final['eval_passed'] is False
    assert final['retry_count'] == MAX_RETRIES + 1


@pytest.mark.asyncio
async def test_pipeline_quiz_and_flashcards_are_structured() -> None:
    quiz = await build_pipeline(llm=FakeChatModel(), retriever=_chunks).ainvoke(_state('quiz'))
    assert quiz['eval_passed'] is True
    assert len(quiz['structured']['questions']) == 3

    cards = await build_pipeline(llm=FakeChatModel(), retriever=_chunks).ainvoke(_state('flashcards'))
    assert cards['structured']['items'][0]['front'] == 'What is variance?'
