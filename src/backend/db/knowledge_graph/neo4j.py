# src/backend/db/knowledge_graph/neo4j.py

from __future__ import annotations

from neo4j import GraphDatabase


class Neo4jClient:

    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
    ):

        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
        )

    def close(self) -> None:
        self.driver.close()

    def create_node(
        self,
        name: str,
        entity_type: str,
        description: str,
        book_id: str,
        page_number: int,
    ) -> None:

        with self.driver.session() as session:

            session.run(
                """
                MERGE (n:Entity {
                    name: $name,
                    type: $entity_type
                })
                SET
                    n.description = $description,
                    n.book_id = $book_id,
                    n.page_number = $page_number
                """,
                name=name,
                entity_type=entity_type,
                description=description,
                book_id=book_id,
                page_number=page_number,
            )

    def create_relationship(
        self,
        source: str,
        target: str,
        relationship_type: str,
        evidence: str,
    ) -> None:

        with self.driver.session() as session:

            query = f"""
                MATCH (a:Entity {{name: $source}})
                MATCH (b:Entity {{name: $target}})
                MERGE (a)-[r:{relationship_type}]->(b)
                SET r.evidence = $evidence
            """

            session.run(
                query,
                source=source,
                target=target,
                evidence=evidence,
            )

    def query(
        self,
        cypher: str,
        parameters: dict | None = None,
    ):

        with self.driver.session() as session:

            result = session.run(
                cypher,
                parameters or {},
            )

            return [
                record.data()
                for record in result
            ]