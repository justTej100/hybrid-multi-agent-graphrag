# integration

These tests are marked integration and stay out of `make test`. `make test-integration` starts the containers in `docker-compose.test.yml`, runs this folder, and tears the containers down.

`conftest.py` skips the module when Postgres on port 55432 cannot be reached. The Neo4j check skips only the graph test when Bolt on port 7688 is down. The fixture points `DATABASE_URL` at the compose database, clears Neo4j settings unless a test turns them back on, truncates documents, chat usage, and study sessions, and signs in as the admin. Embeddings use the hash embedder. Graph extraction uses the fake extractor. The chat model is still the fake, so the test checks wiring and retrieval rather than a live Gemini answer.

`test_end_to_end.py` has three stories. Schema setup and an uploaded PDF produce chunks and vectors, a scoped chat cites that book, and deleting the document removes the chunks. Subscriptions and the guest usage counter survive in Postgres. With Neo4j enabled, ingestion writes entities and a later graph search returns the related fact.

This is the check that `schema.sql`, the halfvec index, the ingestion job, and the optional graph path work on real databases. The fast suite cannot see those SQL and Cypher details.
