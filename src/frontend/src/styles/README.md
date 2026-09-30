# styles

`global.css` is the only stylesheet. `main.tsx` imports it once. There is no CSS framework.

It sets the dark background, the type, the nav, the page width, form fields, buttons, the library list, and the admin stats. The search home is a centered column with a wide rounded field. Study, quiz, flashcards, and graph share a two-column grid. The answer or the cards sit on the left. The PDF pane stays tall on a desktop width so the cited page remains visible. Narrow widths stack the columns.

Citation chips, source rows, quiz choice buttons, flipped flashcards, and graph rows are styled here too. Pages add the right class names and do not ship their own stylesheets.

Changing spacing or type for one screen usually means editing this file, then checking the other screens that reuse the same classes, especially the nav and the study grid.
