"""Docker service addresses shared by the integration tests.

`tests/conftest.py` puts this directory on `sys.path`, so both the fast
collection and the integration run can import it without a `tests` package.
"""

from __future__ import annotations

import pytest

POSTGRES_URL = 'postgresql://argus:test@127.0.0.1:55432/argus'
NEO4J_URI = 'bolt://127.0.0.1:7688'
NEO4J_PASSWORD = 'testpassword'


def postgres_or_skip() -> None:
    try:
        import psycopg

        with psycopg.connect(POSTGRES_URL, connect_timeout=3) as conn:
            conn.execute('SELECT 1')
    except Exception as exc:
        pytest.skip(
            f'Postgres is not reachable ({exc}). '
            'Start it with: docker compose -f docker-compose.test.yml up -d'
        )


def neo4j_or_skip() -> None:
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(NEO4J_URI, auth=('neo4j', NEO4J_PASSWORD))
        driver.verify_connectivity()
        driver.close()
    except Exception as exc:
        pytest.skip(
            f'Neo4j is not reachable ({exc}). '
            'Start it with: docker compose -f docker-compose.test.yml up -d'
        )
