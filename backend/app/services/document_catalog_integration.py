"""
Document Catalog Integration — bridges Phase 4 document/dataset ingestion
with the Phase 8 Enterprise Data Catalog.

Registers ingested documents and extracted datasets as catalog entries,
reusing existing Phase 4 metadata rather than creating a second parser.

Flow: Phase 4 ingestion → Document/Dataset models with metadata →
      DocumentCatalogIntegration → CatalogEntry in Enterprise Catalog
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import structlog

from app.models.catalog_entry import CatalogEntry
from app.models.dataset import Dataset, DatasetColumn
from app.models.document import Document

if TYPE_CHECKING:
    from app.services.catalog_service import CatalogService
    from app.services.semantic_profiler import SemanticMetadataProfiler

logger = structlog.get_logger(__name__)

# File types supported by Phase 4 ingestion
SUPPORTED_DOCUMENT_TYPES = {"pdf", "docx", "txt", "csv", "xls", "xlsx", "json"}

# Mapping from file extensions to human-readable document type labels
FILE_TYPE_LABELS: dict[str, str] = {
    "pdf": "PDF Document",
    "docx": "Word Document",
    "txt": "Text File",
    "csv": "CSV Spreadsheet",
    "xls": "Excel Workbook",
    "xlsx": "Excel Workbook",
    "json": "JSON Data File",
}

# Domain tag heuristics based on file type
FILE_TYPE_DOMAIN_HINTS: dict[str, list[str]] = {
    "pdf": ["documentation", "reports"],
    "docx": ["documentation", "reports"],
    "txt": ["notes", "documentation"],
    "csv": ["data", "structured"],
    "xls": ["data", "structured", "spreadsheet"],
    "xlsx": ["data", "structured", "spreadsheet"],
    "json": ["data", "structured", "configuration"],
}


class DocumentCatalogIntegration:
    """Integrates Phase 4 document/dataset ingestion with the Enterprise Data Catalog.

    Creates catalog entries for ingested documents and extracted datasets,
    enabling the Strands Agent to discover and reason about document-sourced
    information alongside PostgreSQL and MongoDB sources.

    Key principles:
    - Reuses Phase 4 metadata — does NOT parse documents again
    - Represents Excel content heterogeneously (tables, semi-structured, narrative)
    - Documents appear in the catalog alongside database sources from the start
    """

    def __init__(
        self,
        catalog_service: CatalogService,
        semantic_profiler: SemanticMetadataProfiler,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            catalog_service: Service for persisting catalog entries.
            semantic_profiler: Profiler for generating semantic metadata
                from document/dataset technical metadata.
        """
        self._catalog_service = catalog_service
        self._semantic_profiler = semantic_profiler

    async def register_document_in_catalog(
        self, document: Document, source_id: UUID
    ) -> CatalogEntry:
        """Register a Phase 4 document as a catalog entry.

        Takes an already-ingested Document model instance (which has extracted
        metadata from Phase 4 processing) and creates a CatalogEntry with
        source_type="document", object_type="document".

        Args:
            document: Phase 4 Document model with file_name, file_type,
                and metadata_entries populated from ingestion.
            source_id: UUID of the data source this document belongs to.

        Returns:
            The created CatalogEntry instance.
        """
        file_type = self._normalize_file_type(document.file_type)
        document_metadata = self._extract_document_metadata(document)

        # Generate semantic profile using the profiler
        semantic_profile = await self._semantic_profiler.profile_document(
            document=document
        )

        # Build domain tags from file type hints and semantic profile
        domain_tags = self._build_document_domain_tags(
            file_type=file_type,
            document_metadata=document_metadata,
            semantic_tags=semantic_profile.domain_tags,
        )

        # Build fields from document metadata
        fields = self._build_document_fields(document_metadata)

        entry = CatalogEntry(
            id=uuid4(),
            source_id=source_id,
            database_name=None,
            schema_name=None,
            object_name=document.file_name,
            object_type="document",
            fields=fields,
            primary_keys=[],
            foreign_keys=[],
            indexes=[],
            semantic_name=semantic_profile.semantic_name,
            semantic_description=semantic_profile.description,
            domain_tags=domain_tags,
            query_capabilities=semantic_profile.query_capabilities,
            suggested_queries=semantic_profile.suggested_questions,
            confidence=semantic_profile.confidence,
            project_fields=semantic_profile.project_fields,
            version=1,
            discovered_at=datetime.now(timezone.utc),
        )

        stored_count = await self._catalog_service.store_discovery_results(
            source_id=source_id, entries=[entry]
        )

        logger.info(
            "document_registered_in_catalog",
            document_id=str(document.id),
            file_name=document.file_name,
            file_type=file_type,
            source_id=str(source_id),
            stored=stored_count,
        )

        return entry

    async def register_dataset_in_catalog(
        self, dataset: Dataset, source_id: UUID
    ) -> CatalogEntry:
        """Register a Phase 4 extracted dataset as a catalog entry.

        For structured data extracted from CSV/Excel via Phase 4 ingestion.
        Creates a CatalogEntry with source_type="document", object_type="dataset".

        Args:
            dataset: Phase 4 Dataset model with name, columns, classification,
                and source_type populated from ingestion.
            source_id: UUID of the data source this dataset belongs to.

        Returns:
            The created CatalogEntry instance.
        """
        # Generate semantic profile using the profiler
        semantic_profile = await self._semantic_profiler.profile_dataset(
            dataset=dataset
        )

        # Build fields from dataset columns
        fields = self._build_dataset_fields(dataset.columns)

        # Build domain tags combining dataset metadata and semantic profile
        domain_tags = self._build_dataset_domain_tags(
            dataset=dataset,
            semantic_tags=semantic_profile.domain_tags,
        )

        # Capture column names for query capabilities
        column_names = [col.name for col in dataset.columns]

        entry = CatalogEntry(
            id=uuid4(),
            source_id=source_id,
            database_name=None,
            schema_name=dataset.sheet_name,  # Sheet name as schema for Excel
            object_name=dataset.name,
            object_type="dataset",
            fields=fields,
            primary_keys=[],
            foreign_keys=[],
            indexes=[],
            semantic_name=semantic_profile.semantic_name,
            semantic_description=semantic_profile.description,
            domain_tags=domain_tags,
            query_capabilities=semantic_profile.query_capabilities,
            suggested_queries=semantic_profile.suggested_questions,
            confidence=semantic_profile.confidence,
            project_fields=semantic_profile.project_fields,
            version=1,
            discovered_at=datetime.now(timezone.utc),
        )

        stored_count = await self._catalog_service.store_discovery_results(
            source_id=source_id, entries=[entry]
        )

        logger.info(
            "dataset_registered_in_catalog",
            dataset_id=str(dataset.id),
            dataset_name=dataset.name,
            source_type=dataset.source_type,
            classification=dataset.classification,
            column_count=len(column_names),
            source_id=str(source_id),
            stored=stored_count,
        )

        return entry

    async def sync_documents_to_catalog(
        self,
        source_id: UUID,
        documents: list[Document],
        datasets: list[Dataset],
    ) -> int:
        """Bulk operation to register all ingested documents/datasets in the catalog.

        Ensures all Phase 4 ingested content from a source is represented
        in the Enterprise Data Catalog. Idempotent — re-running on already-
        cataloged items creates new versions via the catalog service.

        Args:
            source_id: UUID of the data source these items belong to.
            documents: List of Phase 4 Document model instances.
            datasets: List of Phase 4 Dataset model instances.

        Returns:
            Total count of catalog entries created or updated.
        """
        entries_count = 0

        for document in documents:
            try:
                await self.register_document_in_catalog(
                    document=document, source_id=source_id
                )
                entries_count += 1
            except Exception:
                logger.exception(
                    "failed_to_register_document",
                    document_id=str(document.id),
                    file_name=document.file_name,
                    source_id=str(source_id),
                )

        for dataset in datasets:
            try:
                await self.register_dataset_in_catalog(
                    dataset=dataset, source_id=source_id
                )
                entries_count += 1
            except Exception:
                logger.exception(
                    "failed_to_register_dataset",
                    dataset_id=str(dataset.id),
                    dataset_name=dataset.name,
                    source_id=str(source_id),
                )

        logger.info(
            "documents_synced_to_catalog",
            source_id=str(source_id),
            documents_provided=len(documents),
            datasets_provided=len(datasets),
            entries_created=entries_count,
        )

        return entries_count

    # --- Private helpers ---

    def _normalize_file_type(self, file_type: str) -> str:
        """Normalize file type to lowercase without leading dots."""
        normalized = file_type.lower().strip().lstrip(".")
        return normalized

    def _extract_document_metadata(self, document: Document) -> dict[str, str]:
        """Extract key-value metadata from a Document's metadata_entries.

        Collects the metadata that Phase 4 ingestion already extracted
        (title, author, page count, content type indicators, etc.).
        """
        metadata: dict[str, str] = {}
        if hasattr(document, "metadata_entries") and document.metadata_entries:
            for entry in document.metadata_entries:
                metadata[entry.key] = entry.value
        return metadata

    def _build_document_domain_tags(
        self,
        file_type: str,
        document_metadata: dict[str, str],
        semantic_tags: list[str],
    ) -> list[str]:
        """Build domain tags for a document catalog entry.

        Combines:
        1. File-type hints (e.g., pdf → documentation, reports)
        2. Semantic profiler tags
        3. Content indicators from metadata
        """
        tags: set[str] = set()

        # File type hints
        file_hints = FILE_TYPE_DOMAIN_HINTS.get(file_type, [])
        tags.update(file_hints)

        # Semantic profiler tags
        tags.update(semantic_tags)

        # Content indicators from metadata
        content_type = document_metadata.get("content_type", "").lower()
        if "financial" in content_type or "budget" in content_type:
            tags.add("finance")
        if "risk" in content_type:
            tags.add("risk")
        if "schedule" in content_type or "timeline" in content_type:
            tags.add("schedule")
        if "meeting" in content_type or "minutes" in content_type:
            tags.add("meetings")

        # Always include the document source marker
        tags.add("document")

        return sorted(tags)

    def _build_document_fields(self, document_metadata: dict[str, str]) -> list[dict]:
        """Build the fields JSONB structure for a document catalog entry.

        Documents don't have columns like tables, but we represent their
        metadata attributes as fields for catalog consistency.
        """
        fields: list[dict] = []

        # Standard document fields
        standard_fields = [
            ("file_name", "string", "Original file name"),
            ("file_type", "string", "Document format"),
            ("content", "text", "Document text content"),
        ]

        for name, field_type, description in standard_fields:
            fields.append({
                "name": name,
                "field_type": field_type,
                "nullable": False,
                "is_primary_key": False,
                "semantic_label": description,
                "semantic_description": description,
                "is_project_field": False,
                "is_sensitive": False,
            })

        # Add metadata-derived fields
        if "page_count" in document_metadata:
            fields.append({
                "name": "page_count",
                "field_type": "integer",
                "nullable": True,
                "is_primary_key": False,
                "semantic_label": "Page count",
                "semantic_description": "Number of pages in the document",
                "is_project_field": False,
                "is_sensitive": False,
            })

        if "author" in document_metadata:
            fields.append({
                "name": "author",
                "field_type": "string",
                "nullable": True,
                "is_primary_key": False,
                "semantic_label": "Author",
                "semantic_description": "Document author",
                "is_project_field": False,
                "is_sensitive": False,
            })

        if "title" in document_metadata:
            fields.append({
                "name": "title",
                "field_type": "string",
                "nullable": True,
                "is_primary_key": False,
                "semantic_label": "Title",
                "semantic_description": "Document title",
                "is_project_field": False,
                "is_sensitive": False,
            })

        return fields

    def _build_dataset_fields(self, columns: list[DatasetColumn]) -> list[dict]:
        """Build the fields JSONB structure from dataset columns.

        Converts Phase 4 DatasetColumn models into the catalog field format.
        """
        fields: list[dict] = []

        for column in columns:
            fields.append({
                "name": column.name,
                "field_type": column.data_type,
                "nullable": column.nullable,
                "is_primary_key": False,
                "semantic_label": None,
                "semantic_description": None,
                "is_project_field": self._is_project_field(column.name),
                "is_sensitive": False,
            })

        return fields

    def _build_dataset_domain_tags(
        self,
        dataset: Dataset,
        semantic_tags: list[str],
    ) -> list[str]:
        """Build domain tags for a dataset catalog entry.

        Combines:
        1. Source type hints (csv, xlsx)
        2. Dataset classification
        3. Dataset domain (if set)
        4. Semantic profiler tags
        """
        tags: set[str] = set()

        # Source type hints
        source_hints = FILE_TYPE_DOMAIN_HINTS.get(dataset.source_type, [])
        tags.update(source_hints)

        # Dataset classification as a tag
        if dataset.classification:
            tags.add(dataset.classification.lower())

        # Dataset domain
        if dataset.domain:
            tags.add(dataset.domain.lower())

        # Semantic profiler tags
        tags.update(semantic_tags)

        # Always include dataset source marker
        tags.add("dataset")
        tags.add("document")

        return sorted(tags)

    def _is_project_field(self, field_name: str) -> bool:
        """Heuristic check if a field name likely represents a project identifier."""
        project_indicators = {
            "project_id", "project_code", "project_key",
            "project_name", "project_number", "proj_id",
            "proj_code", "project",
        }
        return field_name.lower().strip() in project_indicators
