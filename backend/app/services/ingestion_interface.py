"""
Ingestion interface protocol — clean contract for Phase 5 Strands agent consumption.

Defines the operations that the AI agent can invoke to access ingested data:
- List and query structured datasets
- Search documents via semantic similarity
- Retrieve evidence for source attribution

This protocol is the boundary between the ingestion layer (Phase 4) and
the AI reasoning layer (Phase 5). The agent interacts exclusively through
this interface, never accessing repositories or processors directly.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class IngestionInterface(Protocol):
    """Clean interface contract for Phase 5 Strands agent consumption.

    All methods are async to support database and provider calls.
    Implementations may combine DatasetService + DocumentSearchService
    behind this unified facade.
    """

    async def list_available_datasets(
        self, project_id: UUID | None = None
    ) -> list[dict]:
        """List datasets available for querying.

        Args:
            project_id: Optional project scope. If None, returns all datasets.

        Returns:
            List of dataset summary dicts with: id, name, source_type,
            sheet_name, classification, record_count, status.
        """
        ...

    async def get_dataset_metadata(self, dataset_id: UUID) -> dict:
        """Get full metadata for a specific dataset.

        Args:
            dataset_id: UUID of the dataset.

        Returns:
            Dict with: id, name, columns (schema), record_count, source_type,
            classification, confidence, status, file_name, sheet_name.

        Raises:
            ValueError: If dataset not found.
        """
        ...

    async def query_dataset(self, dataset_id: UUID, query_params: dict) -> dict:
        """Query a structured dataset with filters, sorting, and aggregation.

        Args:
            dataset_id: UUID of the dataset to query.
            query_params: Dict with optional keys: filters, sort, limit, offset,
                columns, aggregations.

        Returns:
            Dict with: records, total_count, aggregations.

        Raises:
            ValueError: If dataset not found.
        """
        ...

    async def search_documents(
        self, project_id: UUID, query: str
    ) -> list[dict]:
        """Semantic search over ingested documents.

        Args:
            project_id: Project to scope the search.
            query: Natural language search query.

        Returns:
            List of evidence dicts with: file_name, page_number, section,
            sheet_name, region, excerpt, similarity_score, document_id, chunk_id.
        """
        ...

    async def get_evidence(
        self, source_id: UUID, evidence_type: str
    ) -> dict:
        """Retrieve specific evidence by source ID and type.

        Args:
            source_id: UUID of the evidence source (chunk_id or dataset_id).
            evidence_type: One of "document" or "structured".

        Returns:
            Dict with evidence details appropriate to the type.

        Raises:
            ValueError: If source not found or evidence_type is invalid.
        """
        ...
