"""
EvalAgent
---------
LCEL chain with structured output (pydantic model) instead of parsing
"VERDICT: PASS/FAIL" strings. Checks ResponseAgent's draft against the
retrieved evidence. Also owns the retry-routing logic used by the
LangGraph conditional edge.
"""

from typing import Callable

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

MAX_RETRIES = 2


class EvalResult(BaseModel):
    passed: bool = Field(description="True if every claim in the draft is supported by the context")
    reason: str = Field(description="One sentence explaining the verdict")


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
    Returns a LangGraph node function bound to the given LLM client.
    """
    eval_chain = EVAL_PROMPT | llm.with_structured_output(EvalResult)

    def eval_agent(state: dict) -> dict:
        context = "\n".join(state["retrieved_chunks"] + state["retrieved_graph_facts"])

        result: EvalResult = eval_chain.invoke(
            {"context": context, "draft_response": state["draft_response"]}
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

from dataclasses import dataclass

from citations import extract_page_citations, is_citation_only


@dataclass
class EvalResult:
    passed: bool
    score: float
    claims_checked: int
    claims_grounded: int
    ungrounded_claims: list[str]
    explanation: str
    citation_errors: list[str]


class EvalAgent:
    """Check page citations and whether the answer contains real prose."""

    def _verify_citations(self, answer_text: str, chunks: list[dict]) -> list[str]:
        if is_citation_only(answer_text):
            return ['Answer contained no explanation — only page references.']

        pages_in_chunks = {int(c['page_number']) for c in chunks}
        cited_pages = extract_page_citations(answer_text)
        if not cited_pages:
            return []

        errors: list[str] = []
        for page in cited_pages:
            if page not in pages_in_chunks:
                errors.append(f'Page reference [p{page}] was not in the retrieved excerpts.')
        return errors

    async def run_on_chunks(self, *, brief: str, chunks: list[dict]) -> EvalResult:
        citation_errors = self._verify_citations(brief, chunks)
        return EvalResult(
            passed=not citation_errors,
            score=1.0 if not citation_errors else 0.5,
            claims_checked=0,
            claims_grounded=0,
            ungrounded_claims=[],
            explanation='Page citation check.',
            citation_errors=citation_errors,
        )
