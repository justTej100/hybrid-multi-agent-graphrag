
"""Post-generation citation verification (no extra LLM call).

Checks that answers contain real prose (not just [pN] tags) and that cited
pages appeared in the retrieved chunk set.
"""
"""
EvalAgent
---------
Checks ResponseAgent's draft against the retrieved evidence. Also owns the
retry-routing logic used by the LangGraph conditional edge.
"""

from typing import Callable

MAX_RETRIES = 2


def make_eval_node(llm) -> Callable[[dict], dict]:
    """
    Returns a LangGraph node function bound to the given LLM client.
    """

    def eval_agent(state: dict) -> dict:
        context = "\n".join(state["retrieved_chunks"] + state["retrieved_graph_facts"])

        prompt = (
            "You are a strict fact-checker. Given the CONTEXT and the DRAFT below, "
            "determine if every claim in the draft is supported by the context.\n"
            "Respond in exactly this format:\n"
            "VERDICT: PASS or FAIL\n"
            "REASON: <one sentence>\n\n"
            f"CONTEXT:\n{context}\n\nDRAFT:\n{state['draft_response']}"
        )
        result = llm.invoke(prompt).content

        passed = "VERDICT: PASS" in result
        reason = result.split("REASON:")[-1].strip() if "REASON:" in result else result

        return {**state, "eval_passed": passed, "eval_feedback": None if passed else reason}

    return eval_agent


def route_after_eval(state: dict) -> str:
    """Conditional edge: decide whether to end or loop back to RefinerAgent."""
    if state["eval_passed"]:
        return "end"
    if state["retry_count"] >= MAX_RETRIES:
        return "end"  # give up gracefully rather than looping forever
    return "retry"


def increment_retry(state: dict) -> dict:
    return {**state, "retry_count": state["retry_count"] + 1}
    
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
