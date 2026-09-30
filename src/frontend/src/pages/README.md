# pages

These are the screens `App.tsx` mounts. They share `Layout` for the nav. Data comes from `api.ts`. The PDF pane is `PdfViewer`. Cited prose is `AnswerBlock`.

`HomePage.tsx` is `/`. It is a centered search field and a count of textbooks whose status is ready. Enter navigates to `/study` with the question in the query string. It does not call the chat route itself.

`StudyPage.tsx` is `/study`. A question from the home screen is sent as a chat over the whole library, or over one textbook when the link from Library includes a document id. The answer is on the left. The first source opens the PDF on the right, scrolled to that page. Later page chips and source rows move the same viewer. Follow-up questions stay in the thread. For an admin, the response session id is kept and sent on the next turn, and opening this screen without a new question loads the latest saved thread. A guest thread is only React state, so a refresh clears it.

`LibraryPage.tsx` is `/library`. It lists textbooks, filters them, previews a PDF, and shows flashcard signup. Admins upload, delete, bulk delete, and open or close signup. Guests can subscribe when signup is open. A ready textbook links into Study for that document. The primary button returns to Search.

`QuizPage.tsx` is `/quiz`. The field placeholder is Quiz me on. The chat mode is quiz. The screen reads `structured.questions`, draws each choice as a button, and after a pick marks the correct one. `[pN]` chips open the PDF beside the questions.

`FlashcardsPage.tsx` is `/flashcards`. The field placeholder is Make flashcards about. The chat mode is flashcards. The screen reads `structured.items`. A click flips front and back. Citation chips open the PDF. Email me calls the flashcard email route. Admins also get Send to subscribers, which broadcasts using the document id on the first source.

`GraphPage.tsx` is `/graph`. It loads the graph JSON and lists nodes and edges with names, types, relationship labels, evidence, and pages. If the enabled flag is false, it says the graph is off. Clicking a page opens `PdfViewer` when `book_id` is a document id.

`LoginPage.tsx` is `/login`. It starts Google sign-in and shows error messages from the query string when OAuth fails.

`AdminPage.tsx` is `/admin` and is linked as Database. It loads admin config, document and vector counts, and sample chunks. The route is still wrapped like the others. The API rejects non-admins, and the nav hides the link unless `/me` says the person is an admin.
