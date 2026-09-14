# src/backend/db/pdf.py

from __future__ import annotations

import fitz


def extract_pages(
    pdf_path: str,
    document_id: str,
) -> list[dict]:

    pdf = fitz.open(pdf_path)

    pages = []

    for page_number, page in enumerate(
        pdf,
        start=1,
    ):

        text = page.get_text("text")

        pages.append(
            {
                "document_id": document_id,
                "page_number": page_number,
                "text": text,
            }
        )

    pdf.close()

    return pages