"""
ResponseAgent
-------------
Generates the user-facing output from retrieved content. Branches on
`mode` ("answer" vs "quiz") but stays a single node/agent.
"""

from typing import Callable


def make_response_node(llm) -> Callable[[dict], dict]:
    """
    Returns a LangGraph node function bound to the given LLM client.
    """

    def response_agent(state: dict) -> dict:
        context = "\n".join(state["retrieved_chunks"] + state["retrieved_graph_facts"])

        if state["mode"] == "answer":
            prompt = (
                "Using ONLY the context below, answer the user's question. "
                "If the context doesn't contain the answer, say so explicitly.\n\n"
                f"Context:\n{context}\n\nQuestion: {state['user_input']}"
            )
        else:  # quiz mode
            prompt = (
                "Using ONLY the context below, write 3 quiz questions (multiple choice) "
                "with the correct answer clearly marked, testing understanding of the "
                "material.\n\n"
                f"Context:\n{context}"
            )

        draft = llm.invoke(prompt).content
        return {**state, "draft_response": draft}

    return response_agent