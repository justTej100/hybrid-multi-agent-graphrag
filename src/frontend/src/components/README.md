# components

Shared pieces used by the pages. They do not own routes. Pages pass data in and receive clicks back.

`Layout.tsx` wraps every signed-in screen. It provides the current user and draws the nav. Search stays highlighted on the home screen and on the study screen, because study is the result of a search. Library, Quiz, Flashcards, and Graph are always shown. Database is shown for admins. The signed-in email is shown for an admin. A guest is labeled as rate limited. Logout hits the API logout path.

`ProtectedRoute.tsx` calls the session check before rendering a screen. A missing session sends the person to the login page. This is what keeps the search home behind Google sign-in.

`PdfViewer.tsx` fetches the PDF bytes for a document id with the session cookie and renders them with `react-pdf`. The `page` prop scrolls the viewer to that page. Study, quiz, flashcards, graph, and the library preview all use it. That is how a citation becomes a visible textbook page.

`AnswerBlock.tsx` renders answer markdown and turns `[pN]` markers into buttons. A click tells the parent which document and page to open. Study uses it for assistant messages. The parent picks the document from the message sources.

`ConfirmDeleteModal.tsx` asks before Library deletes one textbook or many. The delete itself stays in `LibraryPage`.
