"""
QueryAgent
----------
The LLM decides which tool(s) to call (vector_search, graph_search). Execution
is dispatched to the async retrieval helpers, because those need `await`.

`state["scope"]` is the same scope dict the API uses
({"type": "library"} or {"type": "document", "document_id": "..."}).
"""

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

Retriever = Callable[[str, dict | None], Awaitable[list[dict]]]


@tool
def vector_search(query: str) -> str:
    """Search the vector store for document chunks relevant to the query.
    Best for specific, fact-level questions ('what does page 12 say about X')."""
    raise NotImplementedError('executed via query_agent node, not called directly')


@tool
def graph_search(query: str) -> str:
    """Traverse the knowledge graph for relationships and higher-level context.
    Best for 'how do these things relate' or 'summarize across documents' questions."""
    raise NotImplementedError('executed via query_agent node, not called directly')


TOOLS = [vector_search, graph_search]


async def _run_vector_search(query: str, scope: dict | None) -> list[dict]:
    """Return chunk dicts with page_number and text so later agents can cite pages."""
    from db.client import get_scope_document_ids, search_chunks

    document_ids = await get_scope_document_ids(scope)
    if not document_ids:
        return []
    return await search_chunks(query, document_ids, limit=12)


async def _run_graph_search(query: str, scope: dict | None) -> str:
    """Return related-concept lines, or an empty string when the graph is off."""
    from db.client import get_kg_adapter, get_scope_document_ids

    adapter = get_kg_adapter()
    if adapter is None:
        return ''

    book_id = None
    if scope and scope.get('type') == 'document':
        document_ids = await get_scope_document_ids(scope)
        book_id = document_ids[0] if document_ids else None

    try:
        rows = await asyncio.to_thread(
            adapter.search_related_concepts,
            query,
            10,
            book_id,
        )
    except Exception:
        logger.exception('Knowledge graph search failed')
        return ''
    lines = []
    for row in rows or []:
        evidence = row.get('evidence') or ''
        lines.append(f"{row.get('source')} {row.get('relationship')} {row.get('target')}: {evidence}".strip())
    return '\n'.join(line for line in lines if line)


def make_query_node(llm, retriever: Retriever | None = None) -> Callable[[dict], dict]:
    """Return an async LangGraph node. Run the graph with `.ainvoke()`."""
    search = retriever or _run_vector_search
    llm_with_tools = llm.bind_tools(TOOLS)

    async def query_agent(state: dict) -> dict:
        query = state['refined_query']
        scope = state.get('scope')

        instruction = (
            'Given this query, decide which tool(s) would best retrieve relevant '
            'information. Call both if the query needs both specific facts and '
            f'broader relationships.\n\nQuery: {query}'
        )
        ai_msg = await llm_with_tools.ainvoke([HumanMessage(content=instruction)])

        tool_calls = ai_msg.tool_calls or [
            {'name': 'vector_search', 'args': {'query': query}},
        ]

        chunks: list[dict] = []
        graph_facts: list[str] = []

        for call in tool_calls:
            name = call.get('name')
            args = call.get('args') or {}
            tool_query = args.get('query') or query
            if name == 'vector_search':
                chunks.extend(await search(tool_query, scope))
            elif name == 'graph_search':
                result = await _run_graph_search(tool_query, scope)
                if result:
                    graph_facts.append(result)

        return {
            **state,
            'retrieved_chunks': chunks,
            'retrieved_graph_facts': graph_facts,
        }

    return query_agent
