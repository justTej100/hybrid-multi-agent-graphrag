# unit

These tests import backend modules directly. They do not start the HTTP server. They use the fakes and the in-memory database from the parent `conftest.py`.

`test_auth.py` checks session cookies, admin detection, and rejected tokens.

`test_rate_limit.py` checks the guest cooldown and the daily cap, and that an admin is not limited.

`test_citations.py` checks `[pN]` parsing and validation against source pages.

`test_email.py` checks flashcard message building and the error raised when Gmail is not configured.

`test_subscriptions.py` checks opening signup, subscribing, unsubscribing, and listing offers in memory.

`test_storage.py` checks local PDF save, load, and delete.

`test_chunking.py` checks that page text becomes chunks with ids, document ids, and page numbers.

`test_embeddings.py` checks the hash embedder shape and that the Gemini embedder is asked for 3072 dimensions.

`test_pipeline.py` runs the LangGraph loop with the fake model. It covers a passing evaluation, a retry, and stopping at the retry limit.

These tests guard the pieces the API routes assemble. A route-level failure that is really a citation or pipeline bug usually shows up here first.
