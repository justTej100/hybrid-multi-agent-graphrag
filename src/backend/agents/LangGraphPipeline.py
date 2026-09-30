"""
Pipeline
--------
Wires the four agents into a LangGraph state machine:

    RefinerAgent -> QueryAgent -> ResponseAgent -> EvalAgent
         ^                                             |
         |______________ retry (fail) ________________|

Run the compiled graph with `.ainvoke()`. Pass `llm=` and `retriever=` to
`build_pipeline` when tests need to stand in for Gemini and pgvector.

Env vars:
    LLM_PROVIDER=gemini      GEMINI_API_KEY=...   GEMINI_MODEL=gemini-2.5-flash
    LLM_PROVIDER=deepseek    DEEPSEEK_API_KEY=...
"""

from typing import Literal, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from agents.EvalAgent import make_eval_node, route_after_eval
from agents.QueryAgent import Retriever, make_query_node
from agents.RefinerAgent import make_refiner_node
from agents.ResponseAgent import make_response_node

DEFAULT_PROVIDER = 'gemini'
StudyMode = Literal['chat', 'quiz', 'flashcards', 'summary']


def get_llm(provider: Optional[str] = None):
    import os

    provider = (provider or os.getenv('LLM_PROVIDER') or DEFAULT_PROVIDER).lower()

    if provider == 'gemini':
        from config import get_chat_model

        return get_chat_model(temperature=0)

    if provider == 'deepseek':
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model='deepseek-chat',
            temperature=0,
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url='https://api.deepseek.com/v1',
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use 'gemini' or 'deepseek')")


class PipelineState(TypedDict, total=False):
    user_input: str
    mode: StudyMode
    scope: Optional[dict]

    refined_query: Optional[str]
    retrieved_chunks: Optional[list[dict]]
    retrieved_graph_facts: Optional[list[str]]

    draft_response: Optional[str]
    structured: Optional[dict]

    eval_passed: Optional[bool]
    eval_feedback: Optional[str]
    eval_detail: Optional[dict]

    retry_count: int


def build_pipeline(provider: Optional[str] = None, llm=None, retriever: Retriever | None = None):
    """Compile the study graph. `llm` and `retriever` override the real services."""
    active_llm = llm if llm is not None else get_llm(provider)

    graph = StateGraph(PipelineState)
    graph.add_node('refiner', make_refiner_node(active_llm))
    graph.add_node('query', make_query_node(active_llm, retriever))
    graph.add_node('response', make_response_node(active_llm))
    graph.add_node('eval', make_eval_node(active_llm))

    graph.set_entry_point('refiner')
    graph.add_edge('refiner', 'query')
    graph.add_edge('query', 'response')
    graph.add_edge('response', 'eval')
    graph.add_conditional_edges(
        'eval',
        route_after_eval,
        {
            'end': END,
            'refiner': 'refiner',
        },
    )
    return graph.compile()
