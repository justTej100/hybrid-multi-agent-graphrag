"""
RefinerAgent
------------
LCEL chain: prompt -> llm -> string output.
Rewrites raw user input (+ EvalAgent feedback on retry) into a retrieval-
ready query (answer mode) or topic description (quiz mode).
"""

from typing import Callable

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Rewrite the user's question into a precise, unambiguous search query "
            "suitable for retrieval against a document database. Expand "
            "abbreviations, resolve vague references, keep it concise. "
            "{feedback_note}",
        ),
        ("human", "{user_input}"),
    ]
)

QUIZ_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Rewrite the user's request into a short topic/section description "
            "that can be used to pull relevant reference material for generating "
            "quiz questions. {feedback_note}",
        ),
        ("human", "{user_input}"),
    ]
)


def make_refiner_node(llm) -> Callable[[dict], dict]:
    """
    Returns an async LangGraph node function bound to the given LLM client.
    """
    answer_chain = ANSWER_PROMPT | llm | StrOutputParser()
    quiz_chain = QUIZ_PROMPT | llm | StrOutputParser()

    async def refiner_agent(state: dict) -> dict:
        feedback_note = (
            f"Previous attempt failed because: {state['eval_feedback']}. "
            "Adjust the query to fix this."
            if state.get("eval_feedback")
            else ""
        )

        chain = answer_chain if state["mode"] == "answer" else quiz_chain
        refined = await chain.ainvoke(
            {"user_input": state["user_input"], "feedback_note": feedback_note}
        )

        return {**state, "refined_query": refined}

    return refiner_agent