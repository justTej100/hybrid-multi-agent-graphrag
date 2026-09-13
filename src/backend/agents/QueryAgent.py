"""
QueryAgent
----------
The LLM decides which tool(s) to call (vector_search, graph_search) based
on the refined query; execution is dispatched manually to your real async
DB calls (Argus's ai.langchain_store + db.client), since those need
`await` and can't run behind a plain sync @tool.invoke().

`state["scope"]` should be the same scope dict your app already uses
elsewhere (e.g. {"type": "library"} or {"type": "document", "document_id": "..."}) —
it flows straight into get_scope_document_ids(), so QueryAgent respects
whatever the user has scoped their question to.
"""

from typing import Callable

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

# Real Argus retrieval layer
from ai.langchain_store import similarity_search, documents_to_chunk_dicts
from db.client import get_scope_document_ids


# These two @tool definitions exist purely to give the LLM a schema to pick
# from via bind_tools(). Their bodies are never actually executed — the
# node below dispatches to the real async implementations based on
# ai_msg.tool_calls, because real retrieval needs `await`.
@tool
def vector_search(query: str) -> str:
    """Search the vector store for document chunks relevant to the query.
    Best for specific, fact-level questions ('what does page 12 say about X')."""
    raise NotImplementedError("executed via query_agent node, not called directly")


@tool
def graph_search(query: str) -> str:
    """Traverse the knowledge graph / community summaries for relationships
    and higher-level context. Best for 'how do these things relate' or
    'summarize across documents' style questions."""
    raise NotImplementedError("executed via query_agent node, not called directly")


TOOLS = [vector_search, graph_search]


async def _run_vector_search(query: str, scope: dict | None) -> list[dict]:
    """Returns structured chunk dicts (not pre-flattened text) so EvalAgent
    can verify page citations against real page_number values."""
    document_ids = await get_scope_document_ids(scope)
    if not document_ids:
        return []
    results = await similarity_search(query, document_ids, limit=12)
    return documents_to_chunk_dicts(results)


async def _run_graph_search(query: str, scope: dict | None) -> str:
    # TODO: wire up your real graph DB (Neo4j / NetworkX) here once the
    # GraphRAG side of ingestion exists. Argus's current stack only has
    # the vector side (argus_vectors), so this stays a stub for now.
    del scope
    return f"[graph search not yet implemented — query was: {query}]"


def make_query_node(llm) -> Callable[[dict], dict]:
    """
    Returns an async LangGraph node function. Requires the graph to be run
    with `.ainvoke()` since real retrieval is async.
    """
    llm_with_tools = llm.bind_tools(TOOLS)

    async def query_agent(state: dict) -> dict:
        query = state["refined_query"]
        scope = state.get("scope")

        instruction = (
            "Given this query, decide which tool(s) would best retrieve relevant "
            "information. Call both if the query needs both specific facts and "
            f"broader relationships.\n\nQuery: {query}"
        )
        ai_msg = await llm_with_tools.ainvoke([HumanMessage(content=instruction)])

        tool_calls = ai_msg.tool_calls or [
            {"name": "vector_search", "args": {"query": query}},
        ]

        chunks: list[dict] = []
        graph_facts: list[str] = []

        for call in tool_calls:
            if call["name"] == "vector_search":
                result = await _run_vector_search(query, scope)
                chunks.extend(result)
            elif call["name"] == "graph_search":
                result = await _run_graph_search(query, scope)
                if result:
                    graph_facts.append(result)

        return {
            **state,
            "retrieved_chunks": chunks,
            "retrieved_graph_facts": graph_facts,
        }

    return query_agent