# src/backend/db/KnowledgeGraphAdapter.py

from __future__ import annotations

from .knowledge_graph.neo4j import Neo4jClient
from .knowledge_graph.extractor import GraphExtractor
from .knowledge_graph.resolver import EntityResolver


ALLOWED_RELATIONSHIPS = {
    "IS_A",
    "USED_FOR",
    "EXTENDS",
    "REQUIRES",
    "RELATED_TO",
    "ESTIMATES",
    "ASSUMES",
    "COMPARED_WITH",
    "APPLIED_TO",
}


class KnowledgeGraphAdapter:

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_username: str,
        neo4j_password: str,
        deepseek_api_key: str,
    ):

        self.neo4j = Neo4jClient(
            uri=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password,
        )

        self.extractor = GraphExtractor(
            api_key=deepseek_api_key,
        )

        self.resolver = EntityResolver()

    def extract_and_store(
        self,
        text: str,
        book_id: str,
        page_number: int,
    ) -> dict:

        graph = self.extractor.extract(text)

        entities = self.resolver.resolve_entities(
            graph.get("entities", [])
        )

        relationships = graph.get(
            "relationships",
            [],
        )

        for entity in entities:

            self.neo4j.create_node(
                name=entity["name"],
                entity_type=entity["type"],
                description=entity["description"],
                book_id=book_id,
                page_number=page_number,
            )

        for relationship in relationships:

            relationship_type = (
                relationship["type"]
                .upper()
            )

            if relationship_type not in ALLOWED_RELATIONSHIPS:
                continue

            self.neo4j.create_relationship(
                source=relationship["source"],
                target=relationship["target"],
                relationship_type=relationship_type,
                evidence=relationship["evidence"],
            )

        return {
            "entities": entities,
            "relationships": relationships,
        }

    def search_related_concepts(
        self,
        concept: str,
        limit: int = 10,
    ):

        return self.neo4j.query(
            """
            MATCH (a:Entity)-[r]->(b:Entity)
            WHERE toLower(a.name) CONTAINS toLower($concept)
            RETURN
                a.name AS source,
                type(r) AS relationship,
                b.name AS target,
                r.evidence AS evidence
            LIMIT $limit
            """,
            {
                "concept": concept,
                "limit": limit,
            },
        )

    def close(self):
        self.neo4j.close()