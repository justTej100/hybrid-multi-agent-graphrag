# api

`test_routes.py` drives the FastAPI app with the in-memory database and the fake model. Ingestion runs inline, so an upload is finished before the response returns.

The file walks the product the UI depends on. Health. Anonymous chat is rejected. An empty user message is rejected. Upload, status, PDF download, delete, and bulk delete follow the admin rules. Chat, summary, quiz, and flashcards return the shapes the screens render, including quiz questions with choices and flashcard items with a front and a back. Guest chats hit the rate limit on the second call. Flashcard offers, subscribe, and broadcast behave. Admin stats and chunk samples are admin only.

Two cases match the session and graph work. An admin chat creates a session that the session list returns, and a follow-up stays on that session. A guest chat does not add a session, and a guest who asks for the session list is forbidden. The graph route, asked for JSON, returns an object with the graph disabled and empty node and edge lists when Neo4j is unset.

When a screen and the API disagree, this file is the contract to fix first. The React pages read the same JSON fields these assertions check.
