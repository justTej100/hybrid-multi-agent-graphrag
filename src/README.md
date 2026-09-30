# src

This folder is the application. It has two parts that ship together.

`backend` is the FastAPI process. It signs people in, stores textbooks, answers questions, and serves the built website.

`frontend` is the React app. People search, read answers, flip flashcards, and look at the graph here. The built files land in `frontend/dist`, and the API serves that folder for the site routes.

A request starts in the browser, the Vite dev server or the built site calls the API, and the API calls the database and the study pipeline under `backend`. Neither side imports the other. They meet over HTTP and a session cookie.
