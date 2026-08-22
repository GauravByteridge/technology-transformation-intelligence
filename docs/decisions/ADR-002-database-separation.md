# ADR-002: Two PostgreSQL Database Separation (App_DB + RAG_DB)

## Status

Accepted

## Context

The platform manages two fundamentally different categories of data:

1. **Application state**: Users, projects, conversations, query history, audit logs, data source configurations — structured relational data with CRUD access patterns.
2. **Document intelligence**: Uploaded documents, text chunks, vector embeddings — write-heavy during ingestion, read-heavy during similarity search, requiring the pgvector extension.

We considered three approaches:

1. **Single database**: All tables in one PostgreSQL database with pgvector enabled
2. **Two logical databases**: Separate `app_db` and `rag_db` on the same PostgreSQL instance
3. **Different database engines**: PostgreSQL for application state, a dedicated vector database (Pinecone, Weaviate) for embeddings

## Decision

The platform maintains **two logical PostgreSQL databases** on the same local instance:

- **App_DB**: Application state (users, projects, conversations, queries, audit logs, data source configs)
- **RAG_DB**: Document embeddings and chunks (documents, document_chunks, embeddings, document_metadata) with the pgvector extension

Both databases use independent Alembic migration tracks and can evolve their schemas independently.

## Reasoning

**Why separate databases instead of a single one:**

- **Different access patterns**: App_DB is mostly small transactional reads/writes. RAG_DB involves large batch writes during ingestion and vector similarity searches during retrieval. Mixing these in one database risks resource contention.
- **Independent evolution**: RAG schema changes (new embedding models, dimension changes, chunking strategy updates) should not require touching application state migrations.
- **Different scaling needs**: If the platform grows, embedding storage and vector search can be scaled or migrated to a specialized vector DB independently of application state.
- **Clearer ownership**: Repository modules know exactly which database they target. There's no confusion about which tables belong where.

**Why not a dedicated vector database (Pinecone, Weaviate, etc.):**

- PostgreSQL + pgvector is sufficient for POC/early production scale
- Keeps the local development stack simple (one PostgreSQL installation)
- Avoids adding a third-party service dependency in Phase 0
- pgvector provides real vector similarity search without mocking
- Migration to a dedicated vector DB remains possible later — the repository abstraction hides the storage engine

**Why same PostgreSQL instance:**

- Simplifies local development — one PostgreSQL installation, two databases
- No additional infrastructure to manage during development
- The separation is logical, not physical — can be split to separate servers when scaling demands it

## Consequences

### Positive

- Schemas evolve independently with their own migration timelines
- Each database can be backed up, restored, and maintained separately
- Clear boundary between application concerns and AI/RAG concerns
- pgvector operations don't affect application query performance
- Easier to reason about data ownership and repository boundaries

### Negative

- Cross-database joins are not possible (must go through service layer)
- Two migration configurations to maintain (alembic.ini + alembic_rag.ini)
- Developers must understand which database a repository targets
- Local setup requires creating two databases instead of one

### Neutral

- A single PostgreSQL instance hosts both — no additional infrastructure
- If scaling needs grow, RAG_DB can be migrated to a dedicated vector database without changing the application layer
- Both databases use the same PostgreSQL version and can share connection pooling configuration
