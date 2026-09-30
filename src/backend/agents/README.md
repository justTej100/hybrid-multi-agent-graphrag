# agents

This folder answers one study request. `api/routers/chat.py` calls `run_study` in `service.py`. That function runs the LangGraph pipeline and maps the final state onto the study response the UI expects, which is the question, the mode, the written answer, the evaluation, the sources, extra meta, and optional structured quiz or flashcard data.

The loop is refiner, then query, then response, then eval. A failed evaluation returns to the refiner. The loop ends after two retries.

Retrieval goes through `db.client`. With `DATABASE_URL` set, that is pgvector. Without it, overlap between the query words and the chunk text is enough for tests. Graph search runs only when the knowledge graph is enabled, and a graph error becomes an empty graph result so the answer can still be written from the textbook chunks.

`LLM_PROVIDER` set to `gemini`, the default, uses `GEMINI_MODEL`. Set to `deepseek`, it uses the DeepSeek key. Tests pass a fake chat model into `build_pipeline` and never call a live model.

## Files

`__init__.py` marks the package. The pipeline imports each agent module by name.

`RefinerAgent.py` rewrites the student question into a retrieval query and carries the requested mode forward. Later retries see the evaluation failure so the next query can aim at missing evidence.

`QueryAgent.py` resolves which ready documents the question may use, runs vector search, and, when the graph is on, asks the knowledge graph for related concepts. Scope is the whole library or one document id. Sources keep the document id, title, page number, and text the UI and the citation checker need.

`ResponseAgent.py` writes the student-facing result. Chat and summary are prose with `[pN]` citations. Quiz is a set of questions, each with choices and the index of the correct choice. Flashcards are items with a front, a back, and citation markers. Those shapes are what the Quiz and Flashcards screens render.

`EvalAgent.py` checks the draft. The result includes whether it passed, a score, how many claims were checked, which claims were grounded, which were not, an explanation, and citation errors. Citation checks use `citations.py` against the sources from the query step.

`LangGraphPipeline.py` wires the four nodes and the retry edge. `build_pipeline` accepts an injected model and retriever so tests can run the same graph without Gemini or Postgres.

`service.py` is the only function the HTTP layer should call. `run_study` invokes the graph. `set_llm` installs the fake or live model for the process. Model API failures become `LLMError` with a status the chat route turns into 502, 503, or 429.
