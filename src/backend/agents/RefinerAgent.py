"""
RefinerAgent
------------
Takes the raw user input (and, on retry, EvalAgent's feedback) and turns it
into a precise query (answer mode) or topic description (quiz mode) that
QueryAgent can retrieve against.
"""

from typing import Callable


def make_refiner_node(llm) -> Callable[[dict], dict]:
    """
    Returns a LangGraph node function bound to the given LLM client.
    `llm` must expose `.invoke(prompt) -> response` with `response.content`
    (this is true for ChatGoogleGenerativeAI, ChatOpenAI/DeepSeek, etc.)
    """

    def refiner_agent(state: dict) -> dict:
        feedback_note = (
            f"\nPrevious attempt failed because: {state['eval_feedback']}\n"
            "Adjust the query to fix this."
            if state.get("eval_feedback")
            else ""
        )

        if state["mode"] == "answer":
            instruction = (
                "Rewrite the user's question into a precise, unambiguous search "
                "query suitable for retrieval against a document database. "
                "Expand abbreviations, resolve vague references, keep it concise."
            )
        else:  # quiz mode
            instruction = (
                "Rewrite the user's request into a short topic/section description "
                "that can be used to pull relevant reference material for generating "
                "quiz questions."
            )

        prompt = f"{instruction}{feedback_note}\n\nUser input: {state['user_input']}"
        refined = llm.invoke(prompt).content

        return {**state, "refined_query": refined}

    return refiner_agent