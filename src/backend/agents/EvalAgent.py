"""
EvalAgent
---------
Two-stage check on ResponseAgent's draft:
  1. Citation-only check (fast, no LLM call) — catches degenerate answers
     that are just [pN] tags with no real explanation, using Argus's
     existing citations.is_citation_only() helper.
  2. Groundedness check (LLM call, structured output) — verifies every
     claim in the draft is supported by the retrieved evidence.

Also owns the retry-routing logic used by the LangGraph conditional edge.
Only checked in "answer" mode — quiz mode's structured QuizSet output
doesn't have free-text citation formatting to worry about.
"""

from typing import Callable

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from citations import extract_page_citations, is_citation_only

MAX_RETRIES = 2


class EvalResult(BaseModel):
    passed: bool = Field(description="True if every claim in the draft is supported by the context")
    reason: str = Field(description="One sentence explaining the verdict")


def _verify_citations(answer_text: str, chunks: list[dict]) -> list[str]:
    """Catches hallucinated page numbers — citing [pN] for a page that was
    never actually retrieved. Deterministic, no LLM call needed."""
    pages_in_chunks = {int(c["page_number"]) for c in chunks}
    cited_pages = extract_page_citations(answer_text)
    if not cited_pages:
        return []

    errors: list[str] = []
    for page in cited_pages:
        if page not in pages_in_chunks:
            errors.append(f"Page reference [p{page}] was not in the retrieved excerpts.")
    return errors


EVAL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a strict fact-checker. Given the CONTEXT and the DRAFT, "
            "determine if every claim in the draft is supported by the context.\n\n"
            "CONTEXT:\n{context}",
        ),
        ("human", "DRAFT:\n{draft_response}"),
    ]
)


def make_eval_node(llm) -> Callable[[dict], dict]:
    """
    Returns an async LangGraph node function bound to the given LLM client.
    """
    eval_chain = EVAL_PROMPT | llm.with_structured_output(EvalResult)

    async def eval_agent(state: dict) -> dict:
        draft = state["draft_response"]
        chunks = state["retrieved_chunks"]

        if state["mode"] == "answer":
            # Stage 1: fast citation-only check (no real explanation).
            if is_citation_only(draft):
                return {
                    **state,
                    "eval_passed": False,
                    "eval_feedback": (
                        "The draft was just page-citation tags with no real explanation. "
                        "Refine the query so ResponseAgent has enough context to write a "
                        "full explanatory answer, not just references."
                    ),
                    "retry_count": state["retry_count"] + 1,
                }

            # Stage 2: fast citation-accuracy check (hallucinated page numbers).
            citation_errors = _verify_citations(draft, chunks)
            if citation_errors:
                return {
                    **state,
                    "eval_passed": False,
                    "eval_feedback": (
                        "Citation errors: " + " ".join(citation_errors) +
                        " Refine the query to retrieve the right pages, or drop unsupported citations."
                    ),
                    "retry_count": state["retry_count"] + 1,
                }

        # Stage 3: LLM groundedness check.
        context = "\n".join(c["text"] for c in chunks) + "\n" + "\n".join(state["retrieved_graph_facts"])
        result: EvalResult = await eval_chain.ainvoke(
            {"context": context, "draft_response": draft}
        )

        new_retry_count = state["retry_count"] if result.passed else state["retry_count"] + 1

        return {
            **state,
            "eval_passed": result.passed,
            "eval_feedback": None if result.passed else result.reason,
            "retry_count": new_retry_count,
        }

    return eval_agent


def route_after_eval(state: dict) -> str:
    """Conditional edge: end if passed, otherwise loop back to RefinerAgent
    (unless we've already hit MAX_RETRIES, in which case give up gracefully)."""
    if state["eval_passed"]:
        return "end"
    if state["retry_count"] > MAX_RETRIES:
        return "end"
    return "refiner"