# knowledge graph

This folder is the Neo4j side of Argus. `KnowledgeGraphAdapter` in the parent folder is what ingestion and the graph route call. The pieces here are the driver, the model that reads a page, and the helper that collapses duplicate names.

The folder is unused when Neo4j or DeepSeek is not configured. Search still works from chunk embeddings alone.

`__init__.py` marks the package.

`neo4j.py` opens the Bolt driver and runs Cypher. Queries return plain records so the graph route can send them as JSON without handing Neo4j node objects to the client.

`extractor.py` sends one page of textbook text to DeepSeek and asks for entities and relationships. Entities have a name, a type, and a description. Relationships have a source, a target, a type such as IS_A or USED_FOR, and a short evidence quote. The adapter stores those on Neo4j nodes labeled Entity, with the book id and page number, and on typed relationships that keep the evidence.

`resolver.py` normalizes entity names and drops duplicates before they are written, so the same concept mentioned twice on a page becomes one node.

During ingestion, `jobs.py` calls the adapter once per page, which uses the extractor and the resolver and then writes through `neo4j.py`. During a question, `QueryAgent` searches those relationships. On the Graph tab, `list_graph` reads a capped slice of the same data back out.
