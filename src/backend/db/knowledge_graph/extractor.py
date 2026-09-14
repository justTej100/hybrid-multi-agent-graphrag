# src/backend/db/knowledge_graph/extractor.py

from __future__ import annotations

import json

from openai import OpenAI


SYSTEM_PROMPT = """
You are extracting a knowledge graph from a statistics textbook.

Identify important statistical concepts and relationships.

Return ONLY valid JSON in this format:

{
    "entities": [
        {
            "name": "...",
            "type": "...",
            "description": "..."
        }
    ],
    "relationships": [
        {
            "source": "...",
            "target": "...",
            "type": "...",
            "evidence": "..."
        }
    ]
}

Focus on meaningful statistical relationships.

Examples of relationship types:

- IS_A
- USED_FOR
- EXTENDS
- REQUIRES
- RELATED_TO
- ESTIMATES
- ASSUMES
- COMPARED_WITH
- APPLIED_TO

Do not create relationships that are not supported by the text.
"""


class GraphExtractor:

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
    ):

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

        self.model = model

    def extract(
        self,
        text: str,
    ) -> dict:

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            temperature=0,
        )

        content = response.choices[0].message.content

        return json.loads(content)