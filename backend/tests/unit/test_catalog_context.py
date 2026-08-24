"""
Unit tests for CatalogContextInjector.

Verifies:
- build_relevant_context combines and deduplicates project + search entries
- Project-mapped entries are prioritized over search-only entries
- max_context_entries limit is respected
- format_for_system_prompt produces a readable semantic information landscape
- Empty catalog produces a meaningful fallback message
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.ai.catalog_context import CatalogContext, CatalogContextInjector


def _make_catalog_entry(
    entry_id: UUID | None = None,
    object_name: str = "test_table",
    object_type: str = "table",
    source_type: str = "postgresql",
    semantic_name: str | None = None,
    semantic_description: str | None = None,
    domain_tags: list[str] | None = None,
    query_capabilities: list[str] | None = None,
    fields: list[dict] | None = None,
) -> MagicMock:
    """Create a mock CatalogEntry with realistic attributes."""
    entry = MagicMock()
    entry.id = entry_id or uuid4()
    entry.object_name = object_name
    entry.object_type = object_type
    entry.semantic_name = semantic_name
    entry.semantic_description = semantic_description
    entry.domain_tags = domain_tags or []
    entry.query_capabilities = query_capabilities or []
    entry.fields = fields or []

    # Mock the data_source relationship
    data_source = MagicMock()
    data_source.source_type = source_type
    entry.data_source = data_source

    return entry


class TestBuildRelevantContext:
    """Tests for CatalogContextInjector.build_relevant_context."""

    @pytest.mark.asyncio
    async def test_returns_project_entries_when_project_id_provided(self) -> None:
        catalog_service = AsyncMock()
        project_id = uuid4()
        project_entry = _make_catalog_entry(object_name="project_finance")

        catalog_service.get_catalog_for_project.return_value = [project_entry]
        catalog_service.search_catalog.return_value = []

        injector = CatalogContextInjector(catalog_service=catalog_service)
        result = await injector.build_relevant_context("budget question", project_id)

        assert result.included_count == 1
        assert result.entries[0].object_name == "project_finance"
        assert result.project_id == project_id
        catalog_service.get_catalog_for_project.assert_called_once_with(project_id)

    @pytest.mark.asyncio
    async def test_does_not_call_project_lookup_without_project_id(self) -> None:
        catalog_service = AsyncMock()
        catalog_service.search_catalog.return_value = []

        injector = CatalogContextInjector(catalog_service=catalog_service)
        result = await injector.build_relevant_context("general question")

        assert result.project_id is None
        catalog_service.get_catalog_for_project.assert_not_called()

    @pytest.mark.asyncio
    async def test_deduplicates_project_and_search_entries(self) -> None:
        catalog_service = AsyncMock()
        project_id = uuid4()
        shared_id = uuid4()

        # Same entry appears in both project and search results
        project_entry = _make_catalog_entry(
            entry_id=shared_id, object_name="project_finance"
        )
        search_entry = _make_catalog_entry(
            entry_id=shared_id, object_name="project_finance"
        )
        unique_search_entry = _make_catalog_entry(object_name="risk_register")

        catalog_service.get_catalog_for_project.return_value = [project_entry]
        catalog_service.search_catalog.return_value = [search_entry, unique_search_entry]

        injector = CatalogContextInjector(catalog_service=catalog_service)
        result = await injector.build_relevant_context("finance risk", project_id)

        # Should have 2 entries (deduplicated), not 3
        assert result.included_count == 2
        assert result.total_available == 2

    @pytest.mark.asyncio
    async def test_project_entries_come_first(self) -> None:
        catalog_service = AsyncMock()
        project_id = uuid4()

        project_entry = _make_catalog_entry(object_name="project_finance")
        search_entry = _make_catalog_entry(object_name="risk_register")

        catalog_service.get_catalog_for_project.return_value = [project_entry]
        catalog_service.search_catalog.return_value = [search_entry]

        injector = CatalogContextInjector(catalog_service=catalog_service)
        result = await injector.build_relevant_context("question", project_id)

        assert result.entries[0].object_name == "project_finance"
        assert result.entries[1].object_name == "risk_register"

    @pytest.mark.asyncio
    async def test_respects_max_context_entries_limit(self) -> None:
        catalog_service = AsyncMock()

        # Create 25 unique entries
        entries = [_make_catalog_entry(object_name=f"table_{i}") for i in range(25)]
        catalog_service.search_catalog.return_value = entries

        injector = CatalogContextInjector(catalog_service=catalog_service, max_context_entries=10)
        result = await injector.build_relevant_context("broad question")

        assert result.included_count == 10
        assert result.total_available == 25

    @pytest.mark.asyncio
    async def test_default_max_context_entries_is_20(self) -> None:
        catalog_service = AsyncMock()

        entries = [_make_catalog_entry(object_name=f"table_{i}") for i in range(30)]
        catalog_service.search_catalog.return_value = entries

        injector = CatalogContextInjector(catalog_service=catalog_service)
        result = await injector.build_relevant_context("question")

        assert result.included_count == 20


class TestFormatForSystemPrompt:
    """Tests for CatalogContextInjector.format_for_system_prompt."""

    def test_empty_context_returns_no_sources_message(self) -> None:
        catalog_service = AsyncMock()
        injector = CatalogContextInjector(catalog_service=catalog_service)

        context = CatalogContext(entries=[], project_id=None, total_available=0, included_count=0)
        result = injector.format_for_system_prompt(context)

        assert result == "No enterprise data sources are currently available."

    def test_formats_postgresql_entry_with_semantic_info(self) -> None:
        catalog_service = AsyncMock()
        injector = CatalogContextInjector(catalog_service=catalog_service)

        entry = _make_catalog_entry(
            object_name="project_finance",
            source_type="postgresql",
            semantic_name="Project Financials",
            semantic_description="Project budget, actual cost, and variance information.",
            domain_tags=["finance", "budget"],
            query_capabilities=["budget analysis", "cost tracking", "variance reporting"],
            fields=[
                {"name": "project_id", "is_project_field": True, "is_primary_key": False},
                {"name": "budget", "is_project_field": False, "is_primary_key": False},
                {"name": "actual_cost", "is_project_field": False, "is_primary_key": False},
            ],
        )

        context = CatalogContext(entries=[entry], project_id=None, total_available=1, included_count=1)
        result = injector.format_for_system_prompt(context)

        assert "Available Enterprise Data Sources:" in result
        assert "Project Financials (PostgreSQL - project_finance):" in result
        assert "Project budget, actual cost, and variance information." in result
        assert "Capabilities: budget analysis, cost tracking, variance reporting" in result
        assert "Domain: finance, budget" in result

    def test_formats_mongodb_entry(self) -> None:
        catalog_service = AsyncMock()
        injector = CatalogContextInjector(catalog_service=catalog_service)

        entry = _make_catalog_entry(
            object_name="project_risks",
            object_type="collection",
            source_type="mongodb",
            semantic_name="Project Risks",
            semantic_description="Current and historical project risk observations.",
            domain_tags=["risk"],
            query_capabilities=["risk tracking", "severity analysis"],
        )

        context = CatalogContext(entries=[entry], project_id=None, total_available=1, included_count=1)
        result = injector.format_for_system_prompt(context)

        assert "Project Risks (MongoDB - project_risks):" in result

    def test_formats_rag_document_entry(self) -> None:
        catalog_service = AsyncMock()
        injector = CatalogContextInjector(catalog_service=catalog_service)

        entry = _make_catalog_entry(
            object_name="meeting_notes",
            object_type="document",
            source_type="document",
            semantic_name="Meeting Notes",
            semantic_description="Project meeting notes and decisions.",
            query_capabilities=["full text search", "section search"],
        )

        context = CatalogContext(entries=[entry], project_id=None, total_available=1, included_count=1)
        result = injector.format_for_system_prompt(context)

        assert "Meeting Notes (RAG - meeting_notes):" in result
        assert "Capabilities: full text search, section search" in result

    def test_shows_truncation_note_when_entries_limited(self) -> None:
        catalog_service = AsyncMock()
        injector = CatalogContextInjector(catalog_service=catalog_service)

        entry = _make_catalog_entry(object_name="table_1", semantic_name="Table One")

        context = CatalogContext(
            entries=[entry], project_id=None, total_available=15, included_count=1
        )
        result = injector.format_for_system_prompt(context)

        assert "14 additional sources available but not shown" in result

    def test_no_truncation_note_when_all_entries_included(self) -> None:
        catalog_service = AsyncMock()
        injector = CatalogContextInjector(catalog_service=catalog_service)

        entry = _make_catalog_entry(object_name="table_1", semantic_name="Table One")

        context = CatalogContext(
            entries=[entry], project_id=None, total_available=1, included_count=1
        )
        result = injector.format_for_system_prompt(context)

        assert "additional sources available" not in result

    def test_falls_back_to_object_name_when_no_semantic_name(self) -> None:
        catalog_service = AsyncMock()
        injector = CatalogContextInjector(catalog_service=catalog_service)

        entry = _make_catalog_entry(
            object_name="raw_table_name",
            source_type="postgresql",
            semantic_name=None,
        )

        context = CatalogContext(entries=[entry], project_id=None, total_available=1, included_count=1)
        result = injector.format_for_system_prompt(context)

        assert "raw_table_name (PostgreSQL - raw_table_name):" in result

    def test_prioritizes_project_and_pk_fields(self) -> None:
        catalog_service = AsyncMock()
        injector = CatalogContextInjector(catalog_service=catalog_service)

        entry = _make_catalog_entry(
            object_name="project_finance",
            semantic_name="Finance",
            fields=[
                {"name": "id", "is_primary_key": True, "is_project_field": False},
                {"name": "project_id", "is_primary_key": False, "is_project_field": True},
                {"name": "budget", "is_primary_key": False, "is_project_field": False},
                {"name": "notes", "is_primary_key": False, "is_project_field": False},
            ],
        )

        context = CatalogContext(entries=[entry], project_id=None, total_available=1, included_count=1)
        result = injector.format_for_system_prompt(context)

        # Key fields line should exist and start with important fields
        assert "Key fields:" in result
