# mail

This folder sends flashcard decks by email. The study screens and the flashcard routes call it after a deck exists. It does not generate cards. The study pipeline does that, and this folder only formats and sends them.

`__init__.py` marks the package and notes that outbound mail lives here.

`gmail.py` builds a plain-text deck with the topic, each card, and citation links from `citations.py`. It sends through Gmail SMTP using `GMAIL_USER` and `GMAIL_APP_PASSWORD`. If those are missing it raises `EmailNotConfiguredError`. The flashcard HTTP route turns that into an error the UI can show. A chat request that asked to email cards as a side effect ignores that error so the answer still returns.

Callers are `api/routers/flashcards.py` for Email me and for the admin broadcast, and `api/routers/chat.py` when a flashcard request sets the email flag.
