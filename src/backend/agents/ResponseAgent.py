"""
ResponseAgent
-------------
LCEL chains: prompt -> llm -> output.
- answer mode: plain string output (the written answer)
- quiz mode: structured output (list of QuizQuestion) via with_structured_output,
  so downstream code gets real objects instead of parsing free text.
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


ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Using ONLY the context below, answer the user's question. "
            "If the context doesn't contain the answer, say so explicitly.\n\n"
            "Context:\n{context}",
        ),
        ("human", "{user_input}"),
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


def make_response_node(llm) -> Callable[[dict], dict]:
    """
    Returns a LangGraph node function bound to the given LLM client.
    """
    answer_chain = ANSWER_PROMPT | llm | StrOutputParser()
    quiz_chain = QUIZ_PROMPT | llm.with_structured_output(QuizSet)

    def response_agent(state: dict) -> dict:
        context = "\n".join(state["retrieved_chunks"] + state["retrieved_graph_facts"])

        if state["mode"] == "answer":
            draft = answer_chain.invoke({"context": context, "user_input": state["user_input"]})
        else:  # quiz mode
            quiz_set: QuizSet = quiz_chain.invoke({"context": context})
            draft = quiz_set.model_dump_json(indent=2)

        return {**state, "draft_response": draft}

    return response_agent