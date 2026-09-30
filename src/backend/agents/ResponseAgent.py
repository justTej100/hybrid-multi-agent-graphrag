"""
ResponseAgent
-------------
Writes the student-facing draft from retrieved chunks.
- chat / summary: prose with [pN] page citations
- quiz / flashcards: structured output
"""

from typing import Callable, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class QuizQuestion(BaseModel):
    question: str = Field(description='The quiz question text')
    choices: List[str] = Field(description='Multiple choice options, 3-5 items')
    correct_choice: str = Field(description='The correct choice, must match one item in choices')


class QuizSet(BaseModel):
    questions: List[QuizQuestion] = Field(description='3 quiz questions generated from the context')


class Flashcard(BaseModel):
    front: str = Field(description='The prompt shown on the front of the card')
    back: str = Field(description='The answer shown on the back of the card')
    citations: List[str] = Field(default_factory=list, description='Page tags such as [p3] that support the card')


class FlashcardSet(BaseModel):
    items: List[Flashcard] = Field(description='Flashcards generated from the context')


ANSWER_SYSTEM = (
    'You are a personal tutor. The student uploaded their textbooks. '
    'Always write a complete answer in your own words — paragraphs that explain and teach. '
    'Use the provided excerpts as your source material. '
    'Page references use [pN] where N is the page number from the source documents. '
    'Put 1-3 page refs at the end on a "References:" line — never make the whole reply '
    'just page tags. Never invent page numbers not shown in the excerpts.\n\n'
    'Context:\n{context}'
)

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ('system', ANSWER_SYSTEM),
        (
            'human',
            'Student question: {user_input}\n\n'
            'Write a helpful tutor answer in markdown.\n'
            '- Minimum 4 sentences of explanation in your own words.\n'
            '- Summarize topics clearly (bullet points if helpful).\n'
            '- End with "References:" and 1-3 page tags like [p1].\n'
            '- NEVER reply with only [pN] tags.',
        ),
    ]
)

SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            'system',
            'Write a clear study summary of the material in the context. '
            'Explain the ideas in your own words. Cite pages with [pN] and end with a References line. '
            'Never invent page numbers that are not in the excerpts.\n\n'
            'Context:\n{context}',
        ),
        ('human', 'Summarize this topic: {user_input}'),
    ]
)

QUIZ_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            'system',
            'Using ONLY the context below, write 3 multiple-choice quiz questions '
            'testing understanding of the material.\n\nContext:\n{context}',
        ),
        ('human', 'Generate the quiz.'),
    ]
)

FLASHCARD_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            'system',
            'Using ONLY the context below, write 4 flashcards. Each card needs a front question, '
            'a back answer, and citations like [pN] taken from the context.\n\nContext:\n{context}',
        ),
        ('human', 'Create the flashcards.'),
    ]
)


def _format_context(chunks: list[dict] | None, graph_facts: list[str] | None) -> str:
    lines = []
    for chunk in chunks or []:
        text = chunk.get('text') or chunk.get('content') or ''
        lines.append(f"[p{chunk['page_number']}] {text}")
    lines.extend(graph_facts or [])
    return '\n\n'.join(lines)


def make_response_node(llm) -> Callable[[dict], dict]:
    """Return an async LangGraph node bound to the given LLM client."""
    answer_chain = ANSWER_PROMPT | llm | StrOutputParser()
    summary_chain = SUMMARY_PROMPT | llm | StrOutputParser()
    quiz_chain = QUIZ_PROMPT | llm.with_structured_output(QuizSet)
    flash_chain = FLASHCARD_PROMPT | llm.with_structured_output(FlashcardSet)

    async def response_agent(state: dict) -> dict:
        context = _format_context(state.get('retrieved_chunks'), state.get('retrieved_graph_facts'))
        mode = state.get('mode') or 'chat'
        payload = {'context': context, 'user_input': state['user_input']}

        structured = None
        if mode == 'quiz':
            quiz_set: QuizSet = await quiz_chain.ainvoke({'context': context})
            draft = quiz_set.model_dump_json(indent=2)
            structured = quiz_set.model_dump()
        elif mode == 'flashcards':
            deck: FlashcardSet = await flash_chain.ainvoke({'context': context})
            draft = deck.model_dump_json(indent=2)
            structured = deck.model_dump()
        elif mode == 'summary':
            draft = await summary_chain.ainvoke(payload)
        else:
            draft = await answer_chain.ainvoke(payload)

        return {**state, 'draft_response': draft, 'structured': structured}

    return response_agent
