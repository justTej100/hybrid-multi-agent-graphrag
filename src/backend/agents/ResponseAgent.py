"""
ResponseAgent
-------------
LCEL chains: prompt -> llm -> output.
- answer mode: plain string output, using Argus's tutor system prompt with
  [pN] page-citation rules (borrowed from run_study_chain's SYSTEM prompt).
- quiz mode: structured output (list of QuizQuestion) via with_structured_output.
"""

from typing import Callable, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field


class QuizQuestion(BaseModel):
    question: str = Field(description="The quiz question text")
    choices: List[str] = Field(description="Multiple choice options, 3-5 items")
    correct_choice: str = Field(description="The correct choice, must match one item in choices")


class QuizSet(BaseModel):
    questions: List[QuizQuestion] = Field(description="3 quiz questions generated from the context")


# Borrowed from Argus's run_study_chain SYSTEM prompt — keeps citation
# behavior consistent with the rest of the app.
ANSWER_SYSTEM = (
    "You are a personal tutor. The student uploaded their textbooks. "
    "Always write a complete answer in your own words — paragraphs that explain and teach. "
    "Use the provided excerpts as your source material. "
    "Page references use [pN] where N is the page number from the source documents. "
    "Put 1-3 page refs at the end on a \"References:\" line — never make the whole reply "
    "just page tags. Never invent page numbers not shown in the excerpts.\n\n"
    "Context:\n{context}"
)

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", ANSWER_SYSTEM),
        (
            "human",
            "Student question: {user_input}\n\n"
            "Write a helpful tutor answer in markdown.\n"
            "- Minimum 4 sentences of explanation in your own words.\n"
            "- Summarize topics clearly (bullet points if helpful).\n"
            "- End with \"References:\" and 1-3 page tags like [p1].\n"
            "- NEVER reply with only [pN] tags.",
        ),
    ]
)

QUIZ_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Using ONLY the context below, write 3 multiple-choice quiz questions "
            "testing understanding of the material.\n\nContext:\n{context}",
        ),
        ("human", "Generate the quiz."),
    ]
)


def _format_context(chunks: list[dict], graph_facts: list[str]) -> str:
    lines = [f"[p{c['page_number']}] {c['text']}" for c in chunks]
    lines.extend(graph_facts)
    return "\n\n".join(lines)


def make_response_node(llm) -> Callable[[dict], dict]:
    """
    Returns an async LangGraph node function bound to the given LLM client.
    """
    answer_chain = ANSWER_PROMPT | llm | StrOutputParser()
    quiz_chain = QUIZ_PROMPT | llm.with_structured_output(QuizSet)

    async def response_agent(state: dict) -> dict:
        context = _format_context(state["retrieved_chunks"], state["retrieved_graph_facts"])

        if state["mode"] == "answer":
            draft = await answer_chain.ainvoke(
                {"context": context, "user_input": state["user_input"]}
            )
        else:  # quiz mode
            quiz_set: QuizSet = await quiz_chain.ainvoke({"context": context})
            draft = quiz_set.model_dump_json(indent=2)

        return {**state, "draft_response": draft}

    return response_agent