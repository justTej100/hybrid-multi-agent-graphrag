"""
EvalAgent
---------
Checks ResponseAgent's draft:
  1. Citation-only check (no LLM) for chat and summary answers.
  2. Citation accuracy: every [pN] must be a page that was actually retrieved.
  3. Groundedness check (LLM, structured output).

Quiz and flashcard drafts skip the free-text citation checks.
"""

from typing import Callable

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from citations import extract_page_citations, is_citation_only

MAX_RETRIES = 2
_PROSE_MODES = {'chat', 'summary', 'answer'}


class EvalResult(BaseModel):
    passed: bool = Field(description='True if every claim in the draft is supported by the context')
    score: float = Field(description='Groundedness score from 0 to 1')
    claims_checked: int = Field(description='How many claims were checked')
    claims_grounded: int = Field(description='How many of those claims the context supports')
    ungrounded_claims: list[str] = Field(description='Claims that are not supported by the context')
    explanation: str = Field(description='One sentence explaining the verdict')


def _verify_citations(answer_text: str, chunks: list[dict]) -> list[str]:
    """Flag [pN] tags whose page was never retrieved."""
    pages_in_chunks = {int(chunk['page_number']) for chunk in chunks if chunk.get('page_number') is not None}
    cited_pages = extract_page_citations(answer_text)
    errors: list[str] = []
    for page in cited_pages:
        if page not in pages_in_chunks:
            errors.append(f'Page reference [p{page}] was not in the retrieved excerpts.')
    return errors


def _detail(
    *,
    passed: bool,
    score: float,
    claims_checked: int,
    claims_grounded: int,
    ungrounded_claims: list[str],
    explanation: str,
    citation_errors: list[str],
) -> dict:
    return {
        'passed': passed,
        'score': score,
        'claims_checked': claims_checked,
        'claims_grounded': claims_grounded,
        'ungrounded_claims': ungrounded_claims,
        'explanation': explanation,
        'citation_errors': citation_errors,
    }


EVAL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            'system',
            'You are a strict fact-checker. Given the CONTEXT and the DRAFT, '
            'determine if every claim in the draft is supported by the context.\n\n'
            'CONTEXT:\n{context}',
        ),
        ('human', 'DRAFT:\n{draft_response}'),
    ]
)


def make_eval_node(llm) -> Callable[[dict], dict]:
    """Return an async LangGraph node bound to the given LLM client."""
    eval_chain = EVAL_PROMPT | llm.with_structured_output(EvalResult)

    async def eval_agent(state: dict) -> dict:
        draft = state.get('draft_response') or ''
        chunks = state.get('retrieved_chunks') or []
        facts = state.get('retrieved_graph_facts') or []
        mode = state.get('mode') or 'chat'

        if mode in _PROSE_MODES:
            if is_citation_only(draft):
                explanation = (
                    'The draft was just page-citation tags with no real explanation. '
                    'Refine the query so the answer explains the material, not just references.'
                )
                return {
                    **state,
                    'eval_passed': False,
                    'eval_feedback': explanation,
                    'eval_detail': _detail(
                        passed=False,
                        score=0.0,
                        claims_checked=0,
                        claims_grounded=0,
                        ungrounded_claims=[],
                        explanation=explanation,
                        citation_errors=['Answer was only page citations with no explanation.'],
                    ),
                    'retry_count': state['retry_count'] + 1,
                }

            citation_errors = _verify_citations(draft, chunks)
            if citation_errors:
                explanation = 'Citation errors: ' + ' '.join(citation_errors)
                return {
                    **state,
                    'eval_passed': False,
                    'eval_feedback': explanation + ' Refine the query or drop unsupported citations.',
                    'eval_detail': _detail(
                        passed=False,
                        score=0.0,
                        claims_checked=0,
                        claims_grounded=0,
                        ungrounded_claims=[],
                        explanation=explanation,
                        citation_errors=citation_errors,
                    ),
                    'retry_count': state['retry_count'] + 1,
                }

        context_lines = [chunk.get('text') or chunk.get('content') or '' for chunk in chunks]
        context = '\n'.join(context_lines + list(facts))
        result: EvalResult = await eval_chain.ainvoke({'context': context, 'draft_response': draft})
        explanation = result.explanation
        detail = _detail(
            passed=result.passed,
            score=result.score,
            claims_checked=result.claims_checked,
            claims_grounded=result.claims_grounded,
            ungrounded_claims=list(result.ungrounded_claims),
            explanation=explanation,
            citation_errors=[],
        )
        return {
            **state,
            'eval_passed': result.passed,
            'eval_feedback': None if result.passed else explanation,
            'eval_detail': detail,
            'retry_count': state['retry_count'] if result.passed else state['retry_count'] + 1,
        }

    return eval_agent


def route_after_eval(state: dict) -> str:
    """End when the draft passes or retries are exhausted; otherwise refine again."""
    if state.get('eval_passed'):
        return 'end'
    if state.get('retry_count', 0) > MAX_RETRIES:
        return 'end'
    return 'refiner'
