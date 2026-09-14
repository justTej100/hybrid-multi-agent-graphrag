# src/backend/db/knowledge_graph/resolver.py

from __future__ import annotations

import re


class EntityResolver:

    @staticmethod
    def normalize(name: str) -> str:

        name = name.lower().strip()

        name = re.sub(
            r"\s+",
            " ",
            name,
        )

        return name

    def resolve_entities(
        self,
        entities: list[dict],
    ) -> list[dict]:

        unique = {}

        for entity in entities:

            key = self.normalize(
                entity["name"]
            )

            if key not in unique:
                unique[key] = entity

        return list(unique.values())