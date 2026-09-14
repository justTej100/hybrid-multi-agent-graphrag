# src/backend/db/storage.py

from __future__ import annotations

from supabase import create_client


class PDFStorage:

    def __init__(
        self,
        supabase_url: str,
        service_key: str,
        bucket: str = "statistics-books",
    ):

        self.client = create_client(
            supabase_url,
            service_key,
        )

        self.bucket = bucket

    def upload(
        self,
        local_path: str,
        storage_path: str,
    ) -> str:

        with open(local_path, "rb") as file:

            self.client.storage \
                .from_(self.bucket) \
                .upload(
                    storage_path,
                    file,
                )

        return storage_path

    def download(
        self,
        storage_path: str,
        output_path: str,
    ) -> None:

        data = (
            self.client.storage
            .from_(self.bucket)
            .download(storage_path)
        )

        with open(output_path, "wb") as file:
            file.write(data)

    def delete(
        self,
        storage_path: str,
    ) -> None:

        (
            self.client.storage
            .from_(self.bucket)
            .remove([storage_path])
        )