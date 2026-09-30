# Study agents

The study answer is a LangGraph loop:

```text
RefinerAgent -> QueryAgent -> ResponseAgent -> EvalAgent
     ^                                              |
     |________________ retry (fail) ________________|
```

| Module | Role |
| --- | --- |
| `RefinerAgent.py` | Turns the student question into a retrieval query |
| `QueryAgent.py` | Picks vector search and, when Neo4j is configured, graph search |
| `ResponseAgent.py` | Writes chat, summary, quiz, or flashcard output |
| `EvalAgent.py` | Checks citations and groundedness; sends failures back to the refiner |
| `LangGraphPipeline.py` | Wires the four nodes. `build_pipeline(llm=, retriever=)` accepts test doubles |
| `service.py` | `run_study(...)` maps the final graph state onto the `/chat` response |

Retrieval goes through `db.client` (pgvector when `DATABASE_URL` is set, token overlap otherwise). Graph search runs only when `NEO4J_URI`, `NEO4J_PASSWORD`, and `DEEPSEEK_API_KEY` are all set.

`LLM_PROVIDER=gemini` (default) uses `GEMINI_MODEL` (default `gemini-2.5-flash`). `LLM_PROVIDER=deepseek` uses `DEEPSEEK_API_KEY`.
