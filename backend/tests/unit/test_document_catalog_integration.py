"""Unit tests for DocumentCatalogIntegration service."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.models.catalog_entry import CatalogEntry
from app.models.dataset import Dataset, DatasetColumn
from app.models.document import Document, DocumentMetadata
from app.schemas.discovery import SemanticProfile
from app.services.document_catalog_integration import (
    DocumentCatalogIntegration,
    FILE_TYPE_DOMAIN_HINTS,
    FILE_TYPE_LABELS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_document(
    file_name: str = "report.pdf",
    file_type: str = "pdf",
    file_size: int = 1024,
    metadata_entries: list[DocumentMetadata] | None = None,
) -> Document:
    """Create a minimal Document model instance for testing."""
    doc = MagicMock(spec=Document)
    doc.id = uuid4()
    doc.project_id = uuid4()
    doc.source_id = uuid4()
    doc.file_name = file_name
    doc.file_type = file_type
    doc.file_size = file_size
    doc.processing_status = "completed"
    doc.metadata_entries = metadata_entries or []
    return doc


def _make_metadata_entry(key: str, value: str) -> DocumentMetadata:
    """Create a minimal DocumentMetadata instance."""
    entry = MagicMock(spec=DocumentMetadata)
    entry.key = key
    entry.value = value
    return entry


def _make_dataset(
    name: str = "Financial Data",
    source_type: str = "xlsx",
    classification: str = "STRUCTURED",
    sheet_name: str | None = "Sheet1",
    domain: str | None = "finance",
    columns: list[DatasetColumn] | None = None,
) -> Dataset:
    """Create a minimal Dataset model instance for testing."""
    ds = MagicMock(spec=Dataset)
    ds.id = uuid4()
    ds.file_id = uuid4()
    ds.project_id = uuid4()
    ds.name = name
    ds.source_type = source_type
    ds.classification = classification
    ds.sheet_name = sheet_name
    ds.domain = domain
    ds.record_count = 100
    ds.confidence = 0.95
    ds.columns = columns or []
    return ds


def _make_dataset_column(
    name: str, data_type: str = "string", nullable: bool = True, index: int = 0
) -> DatasetColumn:
    """Create a minimal DatasetColumn instance."""
    col = MagicMock(spec=DatasetColumn)
    col.name = name
    col.data_type = data_type
    col.nullable = nullable
    col.column_index = index
    return col


def _make_semantic_profile(
    semantic_name: str = "Project Report",
    description: str = "A project status report",
    domain_tags: list[str] | None = None,
    query_capabilities: list[str] | None = None,
    suggested_questions: list[str] | None = None,
    confidence: str = "medium",
    project_fields: list[str] | None = None,
) -> SemanticProfile:
    """Create a SemanticProfile instance."""
    return SemanticProfile(
        semantic_name=semantic_name,
        description=description,
        domain_tags=domain_tags or ["reports"],
        important_fields=[],
        query_capabilities=query_capabilities or ["status updates"],
        suggested_questions=suggested_questions or ["What is the project status?"],
        confidence=confidence,
        project_fields=project_fields or [],
    )


def _build_integration() -> tuple[
    DocumentCatalogIntegration, AsyncMock, AsyncMock
]:
    """Construct a DocumentCatalogIntegration with mocked dependencies."""
    mock_catalog_service = AsyncMock()
    mock_catalog_service.store_discovery_results = AsyncMock(return_value=1)

    mock_profiler = AsyncMock()
    mock_profiler.profile_document = AsyncMock(
        return_value=_make_semantic_profile()
    )
    mock_profiler.profile_dataset = AsyncMock(
        return_value=_make_semantic_profile(
            semantic_name="Financial Dataset",
            description="Budget and cost data",
            domain_tags=["finance", "budget"],
            query_capabilities=["budget analysis", "cost tracking"],
        )
    )

    integration = DocumentCatalogIntegration(
        catalog_service=mock_catalog_service,
        semantic_profiler=mock_profiler,
    )
    return integration, mock_catalog_service, mock_profiler


# ---------------------------------------------------------------------------
# register_document_in_catalog
# ---------------------------------------------------------------------------


class TestRegisterDocumentInCatalog:
    """Tests for registering a single document in the catalog."""

    @pytest.mark.asyncio
    async def test_creates_catalog_entry_with_document_type(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        doc = _make_document(file_name="status_report.pdf", file_type="pdf")
        source_id = uuid4()

        entry = await integration.register_document_in_catalog(doc, source_id)

        assert entry.object_type == "document"
        assert entry.object_name == "status_report.pdf"
        assert entry.source_id == source_id

    @pytest.mark.asyncio
    async def test_calls_semantic_profiler_with_document(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        doc = _make_document()
        source_id = uuid4()

        await integration.register_document_in_catalog(doc, source_id)

        profiler.profile_document.assert_called_once_with(document=doc)

    @pytest.mark.asyncio
    async def test_stores_entry_via_catalog_service(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        doc = _make_document()
        source_id = uuid4()

        await integration.register_document_in_catalog(doc, source_id)

        catalog_service.store_discovery_results.assert_called_once()
        call_args = catalog_service.store_discovery_results.call_args
        assert call_args.kwargs["source_id"] == source_id
        assert len(call_args.kwargs["entries"]) == 1

    @pytest.mark.asyncio
    async def test_domain_tags_include_file_type_hints(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        doc = _make_document(file_type="pdf")
        source_id = uuid4()

        entry = await integration.register_document_in_catalog(doc, source_id)

        # PDF hints include "documentation" and "reports"
        assert "documentation" in entry.domain_tags
        assert "reports" in entry.domain_tags
        assert "document" in entry.domain_tags

    @pytest.mark.asyncio
    async def test_domain_tags_include_semantic_profiler_tags(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        profiler.profile_document.return_value = _make_semantic_profile(
            domain_tags=["risk", "compliance"]
        )
        doc = _make_document(file_type="docx")
        source_id = uuid4()

        entry = await integration.register_document_in_catalog(doc, source_id)

        assert "risk" in entry.domain_tags
        assert "compliance" in entry.domain_tags

    @pytest.mark.asyncio
    async def test_metadata_entries_influence_domain_tags(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        metadata = [_make_metadata_entry("content_type", "financial report")]
        doc = _make_document(metadata_entries=metadata)
        source_id = uuid4()

        entry = await integration.register_document_in_catalog(doc, source_id)

        assert "finance" in entry.domain_tags

    @pytest.mark.asyncio
    async def test_fields_include_standard_document_fields(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        doc = _make_document()
        source_id = uuid4()

        entry = await integration.register_document_in_catalog(doc, source_id)

        field_names = [f["name"] for f in entry.fields]
        assert "file_name" in field_names
        assert "file_type" in field_names
        assert "content" in field_names

    @pytest.mark.asyncio
    async def test_normalizes_file_type_with_dot_prefix(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        doc = _make_document(file_type=".PDF")
        source_id = uuid4()

        entry = await integration.register_document_in_catalog(doc, source_id)

        # Should still get PDF domain tags
        assert "documentation" in entry.domain_tags


# ---------------------------------------------------------------------------
# register_dataset_in_catalog
# ---------------------------------------------------------------------------


class TestRegisterDatasetInCatalog:
    """Tests for registering a dataset in the catalog."""

    @pytest.mark.asyncio
    async def test_creates_catalog_entry_with_dataset_type(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        ds = _make_dataset(name="Budget Table")
        source_id = uuid4()

        entry = await integration.register_dataset_in_catalog(ds, source_id)

        assert entry.object_type == "dataset"
        assert entry.object_name == "Budget Table"
        assert entry.source_id == source_id

    @pytest.mark.asyncio
    async def test_uses_sheet_name_as_schema(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        ds = _make_dataset(sheet_name="Q4 Financials")
        source_id = uuid4()

        entry = await integration.register_dataset_in_catalog(ds, source_id)

        assert entry.schema_name == "Q4 Financials"

    @pytest.mark.asyncio
    async def test_calls_semantic_profiler_with_dataset(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        ds = _make_dataset()
        source_id = uuid4()

        await integration.register_dataset_in_catalog(ds, source_id)

        profiler.profile_dataset.assert_called_once_with(dataset=ds)

    @pytest.mark.asyncio
    async def test_fields_reflect_dataset_columns(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        columns = [
            _make_dataset_column("project_id", "string", False, 0),
            _make_dataset_column("budget", "decimal", True, 1),
            _make_dataset_column("status", "string", True, 2),
        ]
        ds = _make_dataset(columns=columns)
        source_id = uuid4()

        entry = await integration.register_dataset_in_catalog(ds, source_id)

        field_names = [f["name"] for f in entry.fields]
        assert "project_id" in field_names
        assert "budget" in field_names
        assert "status" in field_names

    @pytest.mark.asyncio
    async def test_project_field_detected_in_columns(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        columns = [
            _make_dataset_column("project_id", "string", False, 0),
            _make_dataset_column("amount", "decimal", True, 1),
        ]
        ds = _make_dataset(columns=columns)
        source_id = uuid4()

        entry = await integration.register_dataset_in_catalog(ds, source_id)

        project_field = next(
            f for f in entry.fields if f["name"] == "project_id"
        )
        assert project_field["is_project_field"] is True

        amount_field = next(
            f for f in entry.fields if f["name"] == "amount"
        )
        assert amount_field["is_project_field"] is False

    @pytest.mark.asyncio
    async def test_domain_tags_include_dataset_domain(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        ds = _make_dataset(domain="finance")
        source_id = uuid4()

        entry = await integration.register_dataset_in_catalog(ds, source_id)

        assert "finance" in entry.domain_tags
        assert "dataset" in entry.domain_tags
        assert "document" in entry.domain_tags

    @pytest.mark.asyncio
    async def test_domain_tags_include_classification(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        ds = _make_dataset(classification="STRUCTURED")
        source_id = uuid4()

        entry = await integration.register_dataset_in_catalog(ds, source_id)

        assert "structured" in entry.domain_tags


# ---------------------------------------------------------------------------
# sync_documents_to_catalog
# ---------------------------------------------------------------------------


class TestSyncDocumentsToCatalog:
    """Tests for bulk sync of documents and datasets."""

    @pytest.mark.asyncio
    async def test_returns_total_count_of_entries_created(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        docs = [_make_document() for _ in range(3)]
        datasets = [_make_dataset() for _ in range(2)]
        source_id = uuid4()

        count = await integration.sync_documents_to_catalog(
            source_id=source_id, documents=docs, datasets=datasets
        )

        assert count == 5

    @pytest.mark.asyncio
    async def test_handles_empty_lists(self) -> None:
        integration, catalog_service, profiler = _build_integration()
        source_id = uuid4()

        count = await integration.sync_documents_to_catalog(
            source_id=source_id, documents=[], datasets=[]
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_continues_on_individual_document_failure(self) -> None:
        integration, catalog_service, profiler = _build_integration()

        # Make the profiler fail on the second call
        call_count = [0]
        original_profile = profiler.profile_document

        async def failing_on_second(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("Profiling failed")
            return _make_semantic_profile()

        profiler.profile_document = AsyncMock(side_effect=failing_on_second)

        docs = [_make_document() for _ in range(3)]
        source_id = uuid4()

        count = await integration.sync_documents_to_catalog(
            source_id=source_id, documents=docs, datasets=[]
        )

        # 2 out of 3 should succeed
        assert count == 2

    @pytest.mark.asyncio
    async def test_continues_on_individual_dataset_failure(self) -> None:
        integration, catalog_service, profiler = _build_integration()

        call_count = [0]

        async def failing_on_first(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Dataset profiling failed")
            return _make_semantic_profile()

        profiler.profile_dataset = AsyncMock(side_effect=failing_on_first)

        datasets = [_make_dataset() for _ in range(2)]
        source_id = uuid4()

        count = await integration.sync_documents_to_catalog(
            source_id=source_id, documents=[], datasets=datasets
        )

        # 1 out of 2 should succeed
        assert count == 1
