# db - Database Layer

The `db/` folder contains everything responsible for storing, retrieving, and managing the data used by the statistics textbook GraphRAG system.

The database layer is split into three main interfaces:

* `PostgresAdapter.py` for relational PostgreSQL data
* `PGvectorAdapter.py` for embeddings and vector search
* `KnowledgeGraphAdapter.py` for the Neo4j knowledge graph

The adapters act as the main API between the rest of the application and the underlying databases. Database-specific implementation details are kept inside the `vector/` and `knowledge_graph/` folders to avoid repeating database logic throughout the project.

## Folder Structure

```text
db/
│
├── PostgresAdapter.py
├── PGvectorAdapter.py
├── KnowledgeGraphAdapter.py
│
├── vector/
│   ├── embeddings.py
│   ├── chunking.py
│   └── ...
│
├── knowledge_graph/
│   ├── extractor.py
│   ├── resolver.py
│   ├── neo4j.py
│   └── ...
│
├── pdf.py
├── storage.py
├── uploadPDF.py
├── schema.sql
└── README.md
```

---

# Architecture

The system uses three separate data stores for different purposes.

```text
                         Statistics Textbooks
                                │
                                ▼
                         Supabase Storage
                                │
                                ▼
                             pdf.py
                                │
                                ▼
                            Chunking
                           /         \
                          /           \
                         ▼             ▼
                PGvectorAdapter   KnowledgeGraphAdapter
                       │                   │
                       ▼                   ▼
                   pgvector              Neo4j
                       │                   │
                       │                   │
                       └─────────┬─────────┘
                                 │
                                 ▼
                         GraphRAG Retrieval
```

PostgreSQL is used alongside pgvector because the two serve different purposes.

```text
Postgres
    │
    ├── Documents
    ├── Chunks
    └── Processing metadata

pgvector
    │
    └── Chunk embeddings

Neo4j
    │
    ├── Concepts
    ├── Methods
    ├── Models
    ├── Relationships
    └── Cross-concept connections
```

---

# Main Database Adapters

These three files are the primary interfaces used by the rest of the application.

## `PostgresAdapter.py`

Provides the application-facing API for normal PostgreSQL data.

It handles information such as:

* Books
* Documents
* PDF metadata
* Chunks
* Processing status
* Page numbers
* Error information

Example responsibilities:

```python
create_document(...)
get_document(...)
list_documents(...)
update_document_status(...)
add_chunks(...)
get_chunks(...)
delete_document(...)
```

The rest of the application should use this adapter instead of directly writing SQL for normal PostgreSQL operations.

---

## `PGvectorAdapter.py`

Provides the application-facing API for vector storage and similarity search.

It handles:

* Creating embeddings
* Storing embeddings
* Searching for similar textbook passages
* Deleting embeddings
* Filtering searches by book

The adapter uses Gemini embeddings and PostgreSQL's `pgvector` extension.

Example responsibilities:

```python
add_chunks(...)
similarity_search(...)
delete_document_vectors(...)
```

The adapter relies on the code inside:

```text
vector/
```

for vector-specific functionality such as chunking and embedding generation.

---

## `KnowledgeGraphAdapter.py`

Provides the application-facing API for the Neo4j knowledge graph.

It handles:

* Extracting entities and relationships
* Creating graph nodes
* Creating graph relationships
* Resolving duplicate concepts
* Searching related concepts
* Managing graph connections

Example responsibilities:

```python
extract_and_store(...)
search_related_concepts(...)
```

The adapter relies on the code inside:

```text
knowledge_graph/
```

for Neo4j and graph-specific implementation.

---

# Vector Folder

## `vector/`

Contains implementation detai
