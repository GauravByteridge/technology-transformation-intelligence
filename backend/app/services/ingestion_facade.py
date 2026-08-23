"""
Ingestion Facade — concrete IngestionInterface implementation.

Bridges the Phase 4 ingestion services (DatasetService, DocumentSearchService)
into the unified IngestionInterface protocol consumed by Phase 5 AI tools.

Uses per-call session management: each method creates a fresh database session,
ensuring proper connection lifecycle and isolation between agent invocations.

Security Invariants:
- Never exposes database sessions, credentials, or connection strings.
- All data access goes through service → repository → database.
- Error messages are domain-scoped (no internal stack details).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class IngestionFacade:
    """Unified facade implementing IngestionInterface for AI tool consumption.

    Creates fresh sessions per operation, assembling the required service
    chain (repository → service) for each call. This ensures that the AI
    tools get proper connection isolation without holding long-lived sessions.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None) -> None:
        """Initialize with a session factory for per-call session creation.

        Args:
            session_factory: Async session factory for App_DB.
                None is accepted for testing but will raise on actual calls.
        """
        self._session_factory = session_factory

    def _require_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Ensure session factory is available.

        Raises:
            RuntimeError: If session factory was not provided.
        """
        if self._session_factory is None:
            raise RuntimeError(
                "IngestionFacade session factory not initialized. "
                "Ensure App_DB is initialized before creating the facade."
            )
        return self._session_factory

    async def list_available_datasets(
        self, project_id: UUID | None = None
    ) -> list[dict]:
        """List datasets available for querying.

        Args:
            project_id: Optional project scope. If None, returns all datasets.

        Returns:
            List of dataset summary dicts.
        """
        factory = self._require_session_factory()

        async with factory() as session:
            from app.repositories.dataset_repository import DatasetRepository
            from app.repositories.file_repository import FileRepository
            from app.services.dataset_service import DatasetService

            dataset_repo = DatasetRepository(session)
            file_repo = FileRepository(session)
            service = DatasetService(
                dataset_repository=dataset_repo,
                file_repository=file_repo,
            )

            return await service.list_datasets(project_id=project_id)

    async def get_dataset_metadata(self, dataset_id: UUID) -> dict:
        """Get full metadata for a specific dataset.

        Args:
            dataset_id: UUID of the dataset.

        Returns:
            Dict with dataset metadata including columns, record count, etc.

        Raises:
            ValueError: If dataset not found.
        """
        factory = self._require_session_factory()

        async with factory() as session:
            from app.repositories.dataset_repository import DatasetRepository
            from app.repositories.file_repository import FileRepository
            from app.services.dataset_service import DatasetService

            dataset_repo = DatasetRepository(session)
            file_repo = FileRepository(session)
            service = DatasetService(
                dataset_repository=dataset_repo,
                file_repository=file_repo,
            )

            return await service.get_dataset_metadata(dataset_id)

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
        factory = self._require_session_factory()

        async with factory() as session:
            from app.repositories.dataset_repository import DatasetRepository
            from app.repositories.file_repository import FileRepository
            from app.services.dataset_service import DatasetService

            dataset_repo = DatasetRepository(session)
            file_repo = FileRepository(session)
            service = DatasetService(
                dataset_repository=dataset_repo,
                file_repository=file_repo,
            )

            return await service.query_dataset(dataset_id, query_params)

    async def search_documents(
        self, project_id: UUID, query: str
    ) -> list[dict]:
        """Semantic search over ingested documents.

        Args:
            project_id: Project to scope the search.
            query: Natural language search query.

        Returns:
            List of evidence dicts ordered by similarity_score descending.
        """
        factory = self._require_session_factory()

        async with factory() as session:
            from app.documents.embedder import DeterministicEmbeddingGenerator
            from app.repositories.document_repository import DocumentRepository
            from app.services.document_search_service import DocumentSearchService

            doc_repo = DocumentRepository(session)

            # Use production embedding generator if available
            try:
                from app.dependencies import get_embedding_provider
                from app.documents.embedder import ProductionEmbeddingGenerator

                embedding_provider = get_embedding_provider()
                embedding_gen = ProductionEmbeddingGenerator(embedding_provider)
            except RuntimeError:
                # Fallback to deterministic embedder for dev/demo
                embedding_gen = DeterministicEmbeddingGenerator()

            service = DocumentSearchService(
                document_repository=doc_repo,
                embedding_generator=embedding_gen,
            )

            return await service.search_documents(
                project_id=project_id,
                query=query,
            )

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
        if evidence_type not in ("document", "structured"):
            raise ValueError(
                f"Invalid evidence_type: '{evidence_type}'. "
                "Must be 'document' or 'structured'."
            )

        factory = self._require_session_factory()

        if evidence_type == "document":
            return await self._get_document_evidence(factory, source_id)
        else:
            return await self._get_structured_evidence(factory, source_id)

    async def _get_document_evidence(
        self,
        factory: async_sessionmaker[AsyncSession],
        chunk_id: UUID,
    ) -> dict:
        """Retrieve document evidence by chunk ID.

        Queries the document chunk directly and joins with the document
        to get file information.

        Args:
            factory: Session factory for creating DB sessions.
            chunk_id: UUID of the document chunk.

        Returns:
            Dict with document evidence fields.

        Raises:
            ValueError: If chunk not found.
        """
        async with factory() as session:
            from sqlalchemy import select

            from app.models.document import Document, DocumentChunk

            statement = (
                select(
                    DocumentChunk.content.label("chunk_content"),
                    DocumentChunk.page_number.label("page_number"),
                    DocumentChunk.section.label("section"),
                    Document.file_name.label("file_name"),
                    Document.id.label("document_id"),
                )
                .select_from(DocumentChunk)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(DocumentChunk.id == chunk_id)
            )

            result = await session.execute(statement)
            row = result.one_or_none()

            if row is None:
                raise ValueError(f"Document chunk not found: {chunk_id}")

            return {
                "file_name": row.file_name,
                "page_number": row.page_number,
                "section": row.section,
                "sheet_name": None,
                "region": None,
                "excerpt": row.chunk_content,
                "similarity_score": 1.0,
                "document_id": str(row.document_id),
                "chunk_id": str(chunk_id),
                "evidence_type": "document",
            }

    async def _get_structured_evidence(
        self,
        factory: async_sessionmaker[AsyncSession],
        dataset_id: UUID,
    ) -> dict:
        """Retrieve structured evidence by dataset ID.

        Args:
            factory: Session factory for creating DB sessions.
            dataset_id: UUID of the dataset.

        Returns:
            Dict with structured evidence fields.

        Raises:
            ValueError: If dataset not found.
        """
        async with factory() as session:
            from app.repositories.dataset_repository import DatasetRepository
            from app.repositories.file_repository import FileRepository
            from app.services.dataset_service import DatasetService

            dataset_repo = DatasetRepository(session)
            file_repo = FileRepository(session)
            service = DatasetService(
                dataset_repository=dataset_repo,
                file_repository=file_repo,
            )

            metadata = await service.get_dataset_metadata(dataset_id)

            return {
                "file_name": metadata.get("source_file", {}).get("file_name", ""),
                "sheet_name": metadata.get("sheet_name"),
                "dataset_id": str(dataset_id),
                "region": None,
                "row_range": f"1-{metadata.get('record_count', 0)}",
                "column_info": [col["name"] for col in metadata.get("columns", [])],
                "records": [],  # Full records not loaded for metadata evidence
                "query_context": f"Dataset: {metadata.get('name', 'unknown')}",
                "evidence_type": "structured",
            }
