"""
Pipeline
--------
Wires the four agents into a LangGraph state machine:

    RefinerAgent -> QueryAgent -> ResponseAgent -> EvalAgent
                       ^                              |
                       |__________ retry (fail) _______|

LLM provider is switchable between Google Gemini and DeepSeek via the
LLM_PROVIDER env var (or by editing DEFAULT_PROVIDER below).

Install what you need:
    pip install langgraph langchain-google-genai langchain-openai

Env vars:
    LLM_PROVIDER=gemini      GOOGLE_API_KEY=...
    LLM_PROVIDER=deepseek    DEEPSEEK_API_KEY=...
"""

import os
from typing import TypedDict, Literal, Optional

from langgraph.graph import StateGraph, END

from refiner_agent import make_refiner_node
from query_agent import make_query_node
from response_agent import make_response_node
from eval_agent import make_eval_node, route_after_eval, increment_retry

DEFAULT_PROVIDER = "gemini"  # "gemini" or "deepseek"


# ---------------------------------------------------------------------------
# LLM factory — swap providers without touching any agent code
# ---------------------------------------------------------------------------
def get_llm(provider: Optional[str] = None):
    provider = (provider or os.getenv("LLM_PROVIDER") or DEFAULT_PROVIDER).lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",  # or "gemini-1.5-flash" for cheaper/faster
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )

    if provider == "deepseek":
        # DeepSeek exposes an OpenAI-compatible API, so ChatOpenAI works
        # with a custom base_url.
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model="deepseek-chat",
            temperature=0,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use 'gemini' or 'deepseek')")


# ---------------------------------------------------------------------------
# Shared state passed between every node
# ---------------------------------------------------------------------------
class PipelineState(TypedDict):
    user_input: str
    mode: Literal["answer", "quiz"]

    refined_query: Optional[str]
    retrieved_chunks: Optional[list[str]]
    retrieved_graph_facts: Optional[list[str]]

    draft_response: Optional[str]

    eval_passed: Optional[bool]
    eval_feedback: Optional[str]

    retry_count: int


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_pipeline(provider: Optional[str] = None):
    llm = get_llm(provider)

    graph = StateGraph(PipelineState)

    graph.add_node("refiner", make_refiner_node(llm))
    graph.add_node("query", make_query_node())
    graph.add_node("response", make_response_node(llm))
    graph.add_node("eval", make_eval_node(llm))
    graph.add_node("bump_retry", increment_retry)

    graph.set_entry_point("refiner")
    graph.add_edge("refiner", "query")
    graph.add_edge("query", "response")
    graph.add_edge("response", "eval")

    graph.add_conditional_edges(
        "eval",
        route_after_eval,
        {
            "end": END,
            "retry": "bump_retry",
        },
    )
    graph.add_edge("bump_retry", "refiner")

    return graph.compile()


# ---------------------------------------------------------------------------
# Example run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = build_pipeline()  # uses LLM_PROVIDER env var, defaults to "gemini"

    initial_state: PipelineState = {
        "user_input": "What were the main risk factors mentioned across the reports?",
        "mode": "answer",
        "refined_query": None,
        "retrieved_chunks": None,
        "retrieved_graph_facts": None,
        "draft_response": None,
        "eval_passed": None,
        "eval_feedback": None,
        "retry_count": 0,
    }

    final_state = app.invoke(initial_state)
    print(final_state["draft_response"])