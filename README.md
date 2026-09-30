# Argus

Argus is a study app for PDF textbooks you upload. After signing in with Google, you ask a question, get an answer that cites pages, and the textbook opens beside the answer on the cited page. The same library can make a quiz or a flashcard deck. When Neo4j and DeepSeek are configured, ingestion also builds a knowledge graph of concepts and relationships, and a Graph tab lets you read it.

The app runs without those extra services. If `DATABASE_URL` is empty, documents and chats that must be remembered stay in memory. If Neo4j is not configured, search still uses the textbook text, and the Graph tab says the graph is off.

## What you can do

Search is the home screen. One field, a line saying how many textbooks are ready, and Enter. The question goes to the study screen over the whole library.

Study puts the answer on the left and the PDF on the right. The viewer opens on the first source. Page chips such as `[p1]` and the source rows jump the viewer to that page in that book.

Library is the textbook list. Admins upload and delete. Guests can read the list and open a book in Study.

Quiz asks you to name a topic, then shows questions with choice buttons. After you pick, the correct choice is revealed. Citation chips open the PDF beside the question.

Flashcards asks for a topic, then shows cards you click to flip. Citation chips open the PDF. Email me sends the deck to you. An admin can also send it to people who subscribed to that textbook.

Graph lists entity names, types, relationship labels, evidence, and page numbers. Clicking a page opens the PDF when the stored book id is a document id.

Database is admin only. It shows how many documents and vectors exist, and a sample of stored chunks.

## Who can do what

Anyone with a Google account can sign in.

`ADMIN_EMAIL` is the admin address. More than one address is allowed, separated by commas. Admins upload and delete textbooks, open or close flashcard signup, email a deck to subscribers, open the database page, and skip the guest chat limits.

Everyone else is a guest. Guests can search, quiz, and make flashcards. Guest chats wait out a cooldown and stop at a daily cap. That usage counter is stored. The questions and answers are not. A guest thread lives in the browser and disappears on refresh.

An admin thread is saved. Opening Study without a new question reloads the latest admin thread.

## How a textbook becomes searchable

1. An admin uploads a PDF from Library. The file goes to local disk or to Supabase Storage.
2. A background job reads the pages, splits them into chunks, and stores the text.
3. Each chunk is embedded and stored for similarity search. Embeddings are 3072 numbers so they match the database column.
4. If the knowledge graph is enabled, each page is mined for entities and relationships and written to Neo4j.
5. The textbook status becomes ready. If a step fails, the status becomes error and the message is kept.
6. Search, quiz, flashcards, and summaries only retrieve textbooks that are ready.

Very short page text is treated as a scan warning on the document. The text that could be read is still stored.

## How a question is answered

The study pipeline is a small loop of four steps.

1. The refiner turns the student question into a retrieval query.
2. The query step searches similar chunks. When the graph is enabled it also looks up related concepts.
3. The response step writes the answer in the requested mode. Modes are chat, quiz, flashcards, and summary. Quiz and flashcards come back as structured data the screens already know how to draw.
4. The eval step checks that page citations point at real retrieved pages and that the answer stays on that evidence. A failed check sends the question back through the loop. The loop stops after two retries.

The chat route records guest usage first, runs that loop, and then, for an admin only, appends the question and the answer to a study session.

## How to run it

You need Python 3.12 or newer and Node 18 or newer. This repo has been run on Python 3.14.

Copy `.env.example` to `.env` and fill in the settings below.

`make install` creates `.venv` and installs the Python packages from `src/backend/requirements.txt`.

`make frontend` installs the UI packages and builds the React app into `src/frontend/dist`.

`make app` installs dependencies, builds the UI, and starts the API on port 8000. Open that site and sign in with Google.

For a live UI while you edit, start the API, then in another terminal run `make frontend-dev`. The Vite server listens on port 5173 and forwards API calls to port 8000.

`make test` runs the fast suite. It does not need Docker.

`make test-integration` starts the Postgres and Neo4j containers in `docker-compose.test.yml`, runs the integration tests, and removes the containers.

`make stop` frees port 8000 on systems that have `lsof`.

On Windows the Makefile uses `.venv/Scripts`. On other systems it uses `.venv/bin`.

## Settings

Put these in `.env` at the repo root. The API loads that file on startup unless `ARGUS_SKIP_DOTENV` is set to `1`, which the test suite does so a developer file cannot leak into tests.

`SECRET_KEY` signs the session cookie. Use a long random string.

`ADMIN_EMAIL` is the Google address with admin rights. Several addresses are separated by commas.

`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` come from a Google Cloud OAuth web client.

`GOOGLE_REDIRECT_URI` must match the redirect registered for that client. Locally that is the path `auth/google/callback` on localhost port 8000.

`GEMINI_API_KEY` is used for embeddings and, by default, for answers. `GEMINI_MODEL` overrides the chat model. The default model is `gemini-2.5-flash`. Embeddings use `models/gemini-embedding-001` at 3072 dimensions.

`LLM_PROVIDER` chooses the answer model. `gemini` is the default. `deepseek` uses `DEEPSEEK_API_KEY` for answers.

`DATABASE_URL` is the Postgres connection string. The database needs the `vector` extension. On startup the API applies `src/backend/db/schema.sql`. Leave this empty to keep data in memory, which is how the fast tests run.

`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `SUPABASE_BUCKET` are for PDF storage in Supabase. The bucket default is `argus-pdfs`. Use the service role key, not the public anon key.

`STORAGE_BACKEND` is `local` or `supabase`. Local files land in `src/backend/uploaded_pdfs`. Production with `ENVIRONMENT` set to `production` defaults to Supabase storage.

`GUEST_CHAT_COOLDOWN_SECONDS` defaults to 300. `GUEST_CHAT_DAILY_LIMIT` defaults to 10.

`GMAIL_USER` and `GMAIL_APP_PASSWORD` turn on flashcard email. Without them, the email actions report that mail is not configured. `APP_BASE_URL` is the site address used inside those emails.

The knowledge graph runs only when all three of these are set. `NEO4J_URI`, `NEO4J_PASSWORD`, and `DEEPSEEK_API_KEY`. `NEO4J_USERNAME` defaults to `neo4j`. DeepSeek is the model that reads each page into entities and relationships. The app still answers questions when this trio is absent.

## Tests

`tests/conftest.py` forces an in-memory database, a fake chat model, and a local upload folder. `tests/fakes.py` holds those stand-ins, including a hash embedder so retrieval can be tested without Gemini.

`make test` covers units and the HTTP routes. An admin chat shows up in the session list. A guest chat does not. The graph route reports that the graph is off when Neo4j is unset.

`make test-integration` uses a real Postgres with pgvector on port 55432 and Neo4j Bolt on port 7688. Those tests skip with a clear message if the containers are down.

## Layout

```text
Makefile                         install, run, and test commands
pytest.ini                       pytest paths and the integration marker
docker-compose.test.yml          Postgres and Neo4j for integration tests
.env.example                     settings template
src/backend                      API, study pipeline, database, ingestion
src/frontend                     React app
tests                            fast tests and Docker-backed tests
```

Each of those folders has its own readme that names every file and how it connects to the running app.

## License

See `LICENSE`.
