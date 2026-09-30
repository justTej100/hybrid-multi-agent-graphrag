# frontend

This is the Argus website. React 19 and Vite draw the screens. React Router switches among them. The PDF viewer uses `react-pdf`. Answers use `react-markdown`. There is no component library and no graph drawing library. The Graph tab is ordinary HTML.

`npm run dev` starts Vite on port 5173. `vite.config.ts` proxies API paths to the FastAPI process on port 8000, including auth, documents, chat, search, flashcards, admin, sessions, graph, health, logout, and `/me`.

`npm run build` typechecks with TypeScript and writes the site to `dist`. The API serves that folder in production and when you use `make app`.

## Files

`package.json` names the scripts and the runtime libraries. `package-lock.json` pins the installed versions.

`index.html` is the shell. It loads the IBM Plex Sans font and mounts the script at `src/main.tsx` into the root node.

`vite.config.ts` is the dev server, the API proxy, and the build output folder.

`tsconfig.json` typechecks the React source. `tsconfig.node.json` typechecks the Vite config. `tsconfig.tsbuildinfo` is a generated cache from `tsc` and is not something to edit.

## Folder

`src` is the application code. See its readme. Pages, shared components, and the stylesheet each have their own readme inside it.

The UI never opens Postgres or Neo4j. It calls the API with the session cookie and renders what comes back. After login the home screen is search. Library, quiz, flashcards, graph, and the admin database page are separate routes that share one navigation bar.
