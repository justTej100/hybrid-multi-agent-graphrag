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

You need Python 3.12 or newer, Node 18 or newer, and a Google account. This repo has been run on Python 3.14.

From the repo root, copy `.env.example` to a file named `.env`. Fill in the keys in the next section before you start the server. The API reads that file on startup.

The smallest set that can sign you in and answer questions is `SECRET_KEY`, `ADMIN_EMAIL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, and `GEMINI_API_KEY`. Leave `STORAGE_BACKEND` as `local`. You can leave `DATABASE_URL` empty for a first run. Textbooks then live in memory and disappear when the process stops.

If `make` is installed, these three commands are enough.

`make install` creates `.venv` and installs the Python packages from `src/backend/requirements.txt`.

`make frontend` installs the UI packages and builds the React app into `src/frontend/dist`.

`make app` installs dependencies, builds the UI, and starts the API on port 8000.

On Windows without `make`, run this from the repo root instead.

```text
py -3 -m venv .venv
.venv\Scripts\pip install -r src\backend\requirements.txt
cd src\frontend
npm install
npm run build
cd ..\..
.venv\Scripts\python -m uvicorn api.main:app --app-dir src/backend --reload --port 8000
```

On macOS or Linux without `make`, use `python3 -m venv .venv`, then `.venv/bin/pip` and `.venv/bin/python` in place of the Windows paths above. The uvicorn line stays the same.

Open the site on localhost port 8000. Choose Sign in with Google. Use the Gmail address you put in `ADMIN_EMAIL`. You land on the search field. Open Library, upload a PDF, and wait until its status is ready. Go back to Search and ask a question. The answer and the cited page open together.

For a live UI while you edit, keep the API running on port 8000 and, in a second terminal, run `make frontend-dev`. The Vite server listens on port 5173 and forwards API calls to port 8000. Without `make`, run `npm run dev` inside `src/frontend`.

`make test` runs the fast suite. It does not need Docker or any of the keys above.

`make test-integration` starts the Postgres and Neo4j containers in `docker-compose.test.yml`, runs the integration tests, and removes the containers.

`make stop` frees port 8000 on systems that have `lsof`. On Windows, stop the terminal that is running uvicorn.

On Windows the Makefile uses `.venv/Scripts`. On other systems it uses `.venv/bin`.

## How to get the keys

Put every value in `.env` at the repo root. Do not commit that file. A line in the file looks like the name, an equals sign, then the value, with no quotes.

### Cookie signing and the admin account

`SECRET_KEY` signs the login cookie. It is not issued by a website. Generate one and paste it in.

```text
py -3 -c "import secrets; print(secrets.token_hex(32))"
```

`ADMIN_EMAIL` is the Gmail address you will use as the admin. That same address must be the one that completes Google sign-in. Several admins are separated by commas.

`GUEST_CHAT_COOLDOWN_SECONDS` defaults to 300. `GUEST_CHAT_DAILY_LIMIT` defaults to 10. Leave them commented out unless you want different guest limits.

### Google sign-in

You need a Google Cloud project and an OAuth web client.

1. Open console.cloud.google.com and create a project, or pick one you already have.
2. Open APIs and Services, then OAuth consent screen. Set the app name and your email. If the app stays in testing, add that same Gmail address as a test user. The scope the app requests is email and profile, which are on the consent screen by default.
3. Open APIs and Services, then Credentials, then Create credentials, then OAuth client ID, then Web application.
4. Under Authorized redirect URIs, add this value exactly.

```text
http://localhost:8000/auth/google/callback
```

5. Copy the client id into `GOOGLE_CLIENT_ID`. Copy the client secret into `GOOGLE_CLIENT_SECRET`.
6. Set `GOOGLE_REDIRECT_URI` to that same redirect string. If this value and the Google Cloud redirect differ by even a slash, login fails.

For a deployed site, add a second redirect that uses your real host and the path `auth/google/callback`, and point `GOOGLE_REDIRECT_URI` at that deployed value.

### Gemini, for embeddings and answers

Answers and textbook embeddings both use Gemini unless you switch the answer model later.

1. Open aistudio.google.com/apikey.
2. Create an API key. You can attach it to the same Google Cloud project.
3. Paste it into `GEMINI_API_KEY`.

`GEMINI_MODEL` overrides the chat model. The default is `gemini-2.5-flash`. Embeddings stay on `models/gemini-embedding-001` at 3072 dimensions. Leave `LLM_PROVIDER` as `gemini`.

A 429 or 503 from chat usually means the Gemini quota or a short outage. Wait, or set `GEMINI_MODEL` to another model your key can call.

### Postgres, so textbooks survive a restart

This block is optional for a first local run. Without `DATABASE_URL`, uploads live only until you stop the server.

Argus expects Postgres with the `vector` extension. Supabase includes it.

1. Create a project at supabase.com/dashboard.
2. Open the project, then Connect, or Project Settings then Database. Copy the URI connection string.
3. Replace the password placeholder with the database password. If the password contains characters such as `@` or `#`, encode them in the URL first. `@` becomes `%40` and `#` becomes `%23`.
4. Paste the whole string as `DATABASE_URL`.

On startup the API runs `src/backend/db/schema.sql`, which creates the tables and the vector index. If the project is paused, wake it from the Supabase dashboard before starting Argus.

### PDF files in the cloud

For local development leave `STORAGE_BACKEND` as `local`. PDFs are written to `src/backend/uploaded_pdfs`.

Use Supabase Storage when you deploy, or whenever you do not want the PDFs only on this machine.

1. In the same Supabase project, open Project Settings, then API.
2. Copy the project URL into `SUPABASE_URL`. It looks like `https://your-project.supabase.co`.
3. Under Project API keys, reveal the `service_role` secret. Paste it into `SUPABASE_SERVICE_KEY`. Do not use the anon key or a key that starts with `sb_publishable`. Those cannot upload files. `SUPABASE_SERVICE_ROLE_KEY` is accepted as another name for the same secret.
4. Create a storage bucket named `argus-pdfs`, or set `SUPABASE_BUCKET` to the bucket you created.
5. Set `STORAGE_BACKEND` to `supabase`.

If `ENVIRONMENT` is `production` and you do not set `STORAGE_BACKEND`, the app chooses Supabase storage on its own. Local development should keep `ENVIRONMENT` as `development`.

### Knowledge graph

Skip this until search, quiz, and flashcards already work. The Graph tab then says the graph is off, which is expected.

The graph turns on only when `NEO4J_URI`, `NEO4J_PASSWORD`, and `DEEPSEEK_API_KEY` are all set. `NEO4J_USERNAME` defaults to `neo4j`.

DeepSeek reads each textbook page into entities and relationships.

1. Open platform.deepseek.com and create an API key.
2. Paste it into `DEEPSEEK_API_KEY`.

Neo4j stores those entities. A local Desktop or server install is enough.

1. Install Neo4j and set a password.
2. Set `NEO4J_URI` to `bolt://localhost:7687` unless your install uses another port.
3. Set `NEO4J_USERNAME` to `neo4j` and `NEO4J_PASSWORD` to the password you chose.

Re-upload a textbook after these three values are set. Pages ingested earlier are not mined for the graph.

`DEEPSEEK_API_KEY` is also how you switch answers off Gemini. Set `LLM_PROVIDER` to `deepseek` only if you want DeepSeek to write the student-facing answers too. The graph extractor uses the DeepSeek key either way.

### Flashcard email

Skip this if you do not need Email me or Send to subscribers. Those buttons report that mail is not configured until Gmail is set.

1. Use a Gmail account with 2-step verification turned on.
2. Open myaccount.google.com/apppasswords and create an app password for Mail.
3. Set `GMAIL_USER` to that Gmail address.
4. Set `GMAIL_APP_PASSWORD` to the 16 character app password.
5. Set `APP_BASE_URL` to the site people open. Locally that is `http://localhost:8000`. Citation links in the email use this address.

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
