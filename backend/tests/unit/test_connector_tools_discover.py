"""
Tests for the discover_available_sources connector tool.

Verifies:
- Returns semantic information landscape from catalog entries
- Groups sources with domain, description, query_capabilities, key_fields
- Handles empty catalog gracefully
- Extracts source_type from the related DataSource
- Parses fields JSONB into key_fields list
- Includes project_id and total_sources in the response
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.ai.tools.connector_tools import create_discover_available_sources


def _make_catalog_entry(
    source_id: str = "22222222-2222-2222-2222-222222222222",
    object_name: str = "project_finance",
    semantic_name: str = "Project Financials",
    semantic_description: str = "Budget, actual cost, and variance data",
    domain_tags: list | None = None,
    query_capabilities: list | None = None,
    fields: list | None = None,
    source_type: str = "postgresql",
) -> MagicMock:
    """Create a mock CatalogEntry with related DataSource."""
    entry = MagicMock()
    entry.source_id = UUID(source_id)
    entry.object_name = object_name
    entry.semantic_name = semantic_name
    entry.semantic_description = semantic_description
    entry.domain_tags = domain_tags or ["finance", "budget"]
    entry.query_capabilities = query_capabilities or [
        "budget tracking",
        "cost analysis",
    ]
    entry.fields = fields or [
        {"name": "budget", "field_type": "numeric"},
        {"name": "actual_cost", "field_type": "numeric"},
        {"name": "variance", "field_type": "numeric"},
    ]

    # Related DataSource
    data_source = MagicMock()
    data_source.source_type = source_type
    entry.data_source = data_source

    return entry


class TestDiscoverAvailableSources:
    """Unit tests for the discover_available_sources AI tool."""

    PROJECT_ID = "11111111-1111-1111-1111-111111111111"

    @pytest.mark.asyncio
    async def test_returns_sources_with_semantic_metadata(self) -> None:
        mock_catalog_service = AsyncMock()
        mock_catalog_service.get_catalog_for_project = AsyncMock(
            return_value=[_make_catalog_entry()]
        )

        tool_fn = create_discover_available_sources(mock_catalog_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["total_sources"] == 1
        assert result["project_id"] == self.PROJECT_ID

        source = result["sources"][0]
        assert source["source_id"] == "22222222-2222-2222-2222-222222222222"
        assert source["source_type"] == "postgresql"
        assert source["semantic_name"] == "Project Financials"
        assert source["domain"] == "Finance"
        assert source["description"] == "Budget, actual cost, and variance data"
        assert source["query_capabilities"] == ["budget tracking", "cost analysis"]
        assert source["key_fields"] == ["budget", "actual_cost", "variance"]
        assert source["object_name"] == "project_finance"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_catalog_entries(self) -> None:
        mock_catalog_service = AsyncMock()
        mock_catalog_service.get_catalog_for_project = AsyncMock(return_value=[])

        tool_fn = create_discover_available_sources(mock_catalog_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["sources"] == []
        assert result["total_sources"] == 0
        assert result["project_id"] == self.PROJECT_ID

    @pytest.mark.asyncio
    async def test_handles_multiple_sources_across_domains(self) -> None:
        entries = [
            _make_catalog_entry(
                source_id="22222222-2222-2222-2222-222222222222",
                object_name="project_finance",
                semantic_name="Project Financials",
                domain_tags=["finance"],
                source_type="postgresql",
            ),
            _make_catalog_entry(
                source_id="33333333-3333-3333-3333-333333333333",
                object_name="risks",
                semantic_name="Project Risks",
                semantic_description="Risk register with severity and status",
                domain_tags=["risk", "compliance"],
                query_capabilities=["risk assessment", "mitigation tracking"],
                fields=[
                    {"name": "severity", "field_type": "string"},
                    {"name": "status", "field_type": "string"},
                ],
                source_type="mongodb",
            ),
        ]

        mock_catalog_service = AsyncMock()
        mock_catalog_service.get_catalog_for_project = AsyncMock(return_value=entries)

        tool_fn = create_discover_available_sources(mock_catalog_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["total_sources"] == 2
        assert result["sources"][0]["domain"] == "Finance"
        assert result["sources"][0]["source_type"] == "postgresql"
        assert result["sources"][1]["domain"] == "Risk"
        assert result["sources"][1]["source_type"] == "mongodb"

    @pytest.mark.asyncio
    async def test_calls_catalog_service_with_parsed_uuid(self) -> None:
        mock_catalog_service = AsyncMock()
        mock_catalog_service.get_catalog_for_project = AsyncMock(return_value=[])

        tool_fn = create_discover_available_sources(mock_catalog_service)
        await tool_fn(self.PROJECT_ID)

        mock_catalog_service.get_catalog_for_project.assert_called_once_with(
            UUID(self.PROJECT_ID)
        )

    @pytest.mark.asyncio
    async def test_falls_back_to_object_name_when_no_semantic_name(self) -> None:
        entry = _make_catalog_entry(semantic_name=None, object_name="raw_table_xyz")
        # MagicMock doesn't properly handle None assignment via keyword
        entry.semantic_name = None

        mock_catalog_service = AsyncMock()
        mock_catalog_service.get_catalog_for_project = AsyncMock(
            return_value=[entry]
        )

        tool_fn = create_discover_available_sources(mock_catalog_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["sources"][0]["semantic_name"] == "raw_table_xyz"

    @pytest.mark.asyncio
    async def test_defaults_domain_to_general_when_no_tags(self) -> None:
        entry = _make_catalog_entry(domain_tags=[])
        entry.domain_tags = []

        mock_catalog_service = AsyncMock()
        mock_catalog_service.get_catalog_for_project = AsyncMock(
            return_value=[entry]
        )

        tool_fn = create_discover_available_sources(mock_catalog_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["sources"][0]["domain"] == "General"

    @pytest.mark.asyncio
    async def test_handles_fields_as_list_of_strings(self) -> None:
        entry = _make_catalog_entry(fields=["col_a", "col_b", "col_c"])
        entry.fields = ["col_a", "col_b", "col_c"]

        mock_catalog_service = AsyncMock()
        mock_catalog_service.get_catalog_for_project = AsyncMock(
            return_value=[entry]
        )

        tool_fn = create_discover_available_sources(mock_catalog_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["sources"][0]["key_fields"] == ["col_a", "col_b", "col_c"]

    @pytest.mark.asyncio
    async def test_handles_missing_data_source_relationship(self) -> None:
        entry = _make_catalog_entry()
        entry.data_source = None

        mock_catalog_service = AsyncMock()
        mock_catalog_service.get_catalog_for_project = AsyncMock(
            return_value=[entry]
        )

        tool_fn = create_discover_available_sources(mock_catalog_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["sources"][0]["source_type"] == "unknown"
