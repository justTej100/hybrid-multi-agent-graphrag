# routers

Each file here is one group of HTTP routes. `api/main.py` mounts them all. They check the session cookie, then call the database, the ingestion job, or the study pipeline. They do not talk to Postgres or Neo4j directly.

`__init__.py` marks the folder as a package. It does not register routes.

`auth.py` is Google sign-in and the session cookie `argus_session`. The cookie is a signed timestamp token, not a row in the database. `require_session` rejects anonymous calls. `require_admin` allows only addresses in `ADMIN_EMAIL`. `is_admin_email` is what the chat route uses when deciding whether to save a thread. This module also serves `/me`, which tells the UI the email, whether the person is an admin, and the guest quota, and `/logout`, which clears the cookie.

`documents.py` lists textbooks for any signed-in user. Upload, delete, bulk delete, and opening flashcard signup are admin only. Upload writes the PDF through `storage` and schedules ingestion through `jobs`. Status, file download for the PDF viewer, and the flashcards-open flag live here too.

`chat.py` is `POST /chat` and the `POST /search` alias. Both require a session. Guests pass through the rate limiter in `rate_limit.py` before the study pipeline runs. The pipeline result is the study response. If the caller is an admin, this module creates or extends a study session and stores the question and the answer, including sources and structured quiz or flashcard data. Guests get the same answer and nothing is inserted for them. `GET /sessions` and `GET /sessions/{id}` are admin only and feed the study screen when an admin returns without a new question. Flashcard mode can also email the deck when the request asks for that.

`flashcards.py` lists textbooks open for signup, subscribes and unsubscribes the signed-in email, emails a deck to that person, and, for an admin, broadcasts a deck to every subscriber of a textbook. Mail failures that mean Gmail is not configured become an HTTP error the UI can show. A best-effort send from the chat route swallows that case so the answer still returns.

`admin.py` is admin only. It returns Supabase dashboard links, document and vector counts, and a short sample of chunks for one textbook. The React database page is the only caller.

`rate_limit.py` enforces the guest cooldown and the daily cap using the `chat_usage` table, or the matching in-memory counter when Postgres is off. Admins skip it. The counter is the only guest data this route writes. It does not store the question.

`graph.py` serves the knowledge graph. A browser navigation asks for HTML and receives the React app, so the Graph tab can load on a refresh. The app fetches the same path and asks for JSON. Signed-in users, including guests, receive entity names, types, descriptions, book ids, page numbers, and relationships with evidence. The list is capped at a few hundred rows. When Neo4j is not configured the JSON is an object whose enabled flag is false and whose node and edge lists are empty. The page then says the graph is off instead of showing an error.
