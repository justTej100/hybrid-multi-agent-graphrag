# frontend source

This folder is the React application. `main.tsx` starts it. `App.tsx` chooses the screen. `api.ts` talks to FastAPI. The pages and components folders do the rest, and `styles/global.css` is the only stylesheet.

Every signed-in screen sits inside `Layout`, which loads the current user from `/me` and draws the nav. Search, Library, Quiz, Flashcards, and Graph are always there. Database appears only for an admin.

## Files

`main.tsx` creates the React root, wraps the app in the router, and imports the global stylesheet.

`App.tsx` declares the routes. `/login` is public. `/` is the search home. `/library`, `/study`, `/quiz`, `/flashcards`, `/graph`, and `/admin` sit behind the session check. Unknown paths return to the home screen.

`api.ts` is the HTTP client. Every call sends the session cookie. It covers documents, chat, sessions, the graph, flashcard email and subscriptions, admin stats, and the PDF file URL. Chat can pass a session id so an admin follow-up stays on one thread. The graph fetch asks for JSON so it does not receive the HTML shell that a normal visit to that path gets. `extractPages` finds `[pN]` markers for citation chips.

`types.ts` is the shared TypeScript shapes. Documents, chat messages, sources, the study response, and the signed-in user live here. The study response matches the API, including evaluation fields and the optional structured quiz or flashcard payload.

`me.tsx` loads `/me` once for the signed-in screens and shares the email, the admin flag, and the guest quota with the nav and the pages that need them.

`vite-env.d.ts` tells TypeScript about Vite client types.

## Folders

`pages` are the screens. See that readme.

`components` are the pieces those screens share. See that readme.

`styles` is the single stylesheet. See that readme.

A search on the home screen navigates to `/study` with the question in the query string. Study calls `api.ts`, which calls `POST /chat`. The response sources open `PdfViewer`. Quiz and flashcards call the same chat route with a different mode and read `structured` questions or items. Graph calls the graph route and draws the rows itself.
