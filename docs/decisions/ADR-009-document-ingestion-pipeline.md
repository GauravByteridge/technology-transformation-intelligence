# ADR-009: Document Ingestion as Separate Pipeline

## Status

Accepted

## Context

The platform supports two categories of data sources:
1. **Structured databases** — PostgreSQL, MongoDB — accessed through connectors with schema discovery and query execution.
2. **File-based documents** — PDF, DOCX, TXT, images — requiring extraction, chunking, embedding, and vector storage.

We needed to decide whether documents should be processed through the same `DataSourceConnector` abstraction used for databases, or through a separate pipeline.

Key differences between the two:
- Databases support real-time queries; documents require pre-processing into searchable chunks.
- Database connectors return structured rows; document processing produces embeddings and semantic search results.
- Database schema is discovered; document structure is extracted and inferred.
- Database queries are SQL/MongoDB-native; document retrieval uses vector similarity search.

## Decision

We implement document ingestion as a **separate, specialized pipeline** (`backend/app/documents/`) that is architecturally independent from the `DataSourceConnector` protocol.

The pipeline follows these stages:

```
File Upload → Validation → Extraction → Chunking → Embedding → Vector Storage (RAG_DB)
```

Components:
- `validator.py` — File type, size, and format validation
- `extractors.py` — Content extraction (PDF, DOCX, TXT)
- `chunker.py` — Text segmentation with positional metadata
- `embedder.py` — Vector generation via configured EmbeddingProvider
- `orchestrator.py` — Coordinates the full pipeline flow
- `pipeline.py` — Pipeline configuration and entry point

At the **product/UI level**, documents may appear alongside database sources in the "Data Sources" view. But the **backend processing** uses this specialized pipeline rather than the connector protocol.

## Reasoning

- **Different processing model** — Databases are queried in real-time; documents must be pre-processed into embeddings. Forcing both into the same interface would mean a leaky abstraction.
- **Different query semantics** — Database connectors use SQL/MongoDB queries; document retrieval uses vector similarity search. The `execute_read()` method semantics don't map cleanly to similarity search.
- **Different data lifecycle** — Documents go through ingestion stages (uploaded → processing → ready → error). Databases are either connected or not. This lifecycle complexity doesn't belong in the connector.
- **Same retrieval mechanism** — Despite separate ingestion, both databases and documents are accessible through AI tools. The agent calls `query_project_finance()` for databases and `search_project_documents()` for documents — same tool pattern, different underlying retrieval.
- **Extensibility** — New file formats (images, spreadsheets) add extractors to the pipeline without touching connectors. New database types add connectors without touching the pipeline.

## Consequences

### Positive

- Each system is optimized for its actual processing model — no awkward abstractions.
- Document pipeline can evolve independently (e.g., add OCR, add spreadsheet parsing) without affecting connector code.
- Clear separation of concerns: connectors for real-time query, pipeline for pre-processed retrieval.
- The AI tool layer provides a unified interface regardless of whether data came from a connector or the document pipeline.
- Pipeline stages are independently testable (validate, extract, chunk, embed separately).

### Negative

- Two different code paths for "getting data" — developers must understand which to use for which source type.
- The UI may need to present both under a unified "Sources" concept while the backend treats them differently.
- Document re-ingestion (when a file is updated) requires pipeline re-execution rather than a simple re-query.
- Monitoring and error handling differ between pipelines — operational tooling needs to cover both.

## Implementation Details

### Pipeline Flow

```
upload_document()
  → validator.validate(file)
  → extractor.extract(file) → raw text
  → chunker.chunk(text) → chunks with metadata
  → embedder.embed(chunks) → vectors
  → repository.store(chunks, vectors) → RAG_DB
```

### AI Integration

The AI agent accesses document data through tools:
- `search_project_documents(project_id, query)` — semantic search across project documents
- `get_document_evidence(document_id, chunk_ids)` — retrieve specific evidence for attribution

These tools use the repository layer to query RAG_DB — they never invoke the pipeline directly.

### Shared Concepts

Both connectors and the document pipeline:
- Are scoped by project (`project_id`)
- Provide source attribution in AI responses
- Use the same structured response contract
- Are accessible only through AI tools (agent never accesses directly)
