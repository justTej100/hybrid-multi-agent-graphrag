# src/backend/db/vector/chunking.py

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[dict]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks = []

    for page in pages:

        text = page["text"]
        page_number = page["page_number"]

        page_chunks = splitter.split_text(text)

        for index, content in enumerate(page_chunks):

            chunk_id = (
                f"{page['document_id']}"
                f"_p{page_number}"
                f"_c{index}"
            )

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": page["document_id"],
                    "page_number": page_number,
                    "content": content,
                }
            )

    return chunks