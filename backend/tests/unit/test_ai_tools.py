"""
Tests for AI domain tool stubs.

Verifies:
- get_project_context returns structured project data via service
- query_project_finance returns connected data sources via service
- Tools call services only — not repositories directly
- Tools include source_label for attribution
- Tools raise appropriate errors for missing projects
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.ai.tools.project_tools import create_get_project_context
from app.ai.tools.finance_tools import create_query_project_finance
from app.errors.project_errors import ProjectNotFoundError
from app.schemas.projects import ProjectResponse
from app.services.data_source_service import DataSourceService


def _make_project_response(
    project_id: str = "11111111-1111-1111-1111-111111111111",
    name: str = "Alpha Transformation",
    description: str = "Enterprise modernization initiative",
    status: str = "active",
) -> ProjectResponse:
    """Create a ProjectResponse for testing."""
    return ProjectResponse(
        id=UUID(project_id),
        name=name,
        description=description,
        status=status,
        created_by=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 6, 1, 14, 30, 0, tzinfo=timezone.utc),
    )


class TestGetProjectContext:
    """Unit tests for the get_project_context AI tool."""

    PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")

    @pytest.mark.asyncio
    async def test_returns_project_info(self) -> None:
        mock_service = AsyncMock()
        mock_service.get_project = AsyncMock(return_value=_make_project_response())

        tool_fn = create_get_project_context(mock_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["project"]["id"] == str(self.PROJECT_ID)
        assert result["project"]["name"] == "Alpha Transformation"
        assert result["project"]["status"] == "active"
        assert result["project"]["description"] == "Enterprise modernization initiative"

    @pytest.mark.asyncio
    async def test_includes_source_label(self) -> None:
        mock_service = AsyncMock()
        mock_service.get_project = AsyncMock(return_value=_make_project_response())

        tool_fn = create_get_project_context(mock_service)
        result = await tool_fn(self.PROJECT_ID)

        assert "source_label" in result
        assert result["source_label"] == "App_DB → projects"

    @pytest.mark.asyncio
    async def test_calls_service_with_project_id(self) -> None:
        mock_service = AsyncMock()
        mock_service.get_project = AsyncMock(return_value=_make_project_response())

        tool_fn = create_get_project_context(mock_service)
        await tool_fn(self.PROJECT_ID)

        mock_service.get_project.assert_called_once_with(self.PROJECT_ID)

    @pytest.mark.asyncio
    async def test_raises_not_found_for_unknown_project(self) -> None:
        mock_service = AsyncMock()
        mock_service.get_project = AsyncMock(
            side_effect=ProjectNotFoundError(project_id="99999999-9999-9999-9999-999999999999")
        )

        tool_fn = create_get_project_context(mock_service)

        with pytest.raises(ProjectNotFoundError):
            await tool_fn(UUID("99999999-9999-9999-9999-999999999999"))


class TestQueryProjectFinance:
    """Unit tests for the query_project_finance AI tool."""

    PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")

    @pytest.mark.asyncio
    async def test_returns_connected_sources(self) -> None:
        mock_service = AsyncMock(spec=DataSourceService)
        mock_service.list_finance_sources_for_project = AsyncMock(
            return_value=[
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "name": "Finance DB",
                    "source_type": "postgresql",
                    "display_label": "Project Finance PostgreSQL",
                    "connection_status": "connected",
                },
            ]
        )

        tool_fn = create_query_project_finance(mock_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["project_id"] == str(self.PROJECT_ID)
        assert result["source_count"] == 1
        assert len(result["connected_sources"]) == 1
        assert result["connected_sources"][0]["name"] == "Finance DB"

    @pytest.mark.asyncio
    async def test_includes_source_label(self) -> None:
        mock_service = AsyncMock(spec=DataSourceService)
        mock_service.list_finance_sources_for_project = AsyncMock(return_value=[])

        tool_fn = create_query_project_finance(mock_service)
        result = await tool_fn(self.PROJECT_ID)

        assert "source_label" in result
        assert result["source_label"] == "App_DB → data_sources, source_connections"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_sources_connected(self) -> None:
        mock_service = AsyncMock(spec=DataSourceService)
        mock_service.list_finance_sources_for_project = AsyncMock(return_value=[])

        tool_fn = create_query_project_finance(mock_service)
        result = await tool_fn(self.PROJECT_ID)

        assert result["source_count"] == 0
        assert result["connected_sources"] == []

    @pytest.mark.asyncio
    async def test_calls_service_with_project_id(self) -> None:
        mock_service = AsyncMock(spec=DataSourceService)
        mock_service.list_finance_sources_for_project = AsyncMock(return_value=[])

        tool_fn = create_query_project_finance(mock_service)
        await tool_fn(self.PROJECT_ID)

        mock_service.list_finance_sources_for_project.assert_called_once_with(
            self.PROJECT_ID
        )


class TestDataSourceService:
    """Unit tests for DataSourceService."""

    PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")

    @pytest.mark.asyncio
    async def test_list_finance_sources_returns_formatted_dicts(self) -> None:
        mock_repository = AsyncMock()
        mock_data_source = MagicMock()
        mock_data_source.id = UUID("22222222-2222-2222-2222-222222222222")
        mock_data_source.name = "Finance DB"
        mock_data_source.source_type = "postgresql"
        mock_data_source.display_label = "Project Finance PostgreSQL"
        mock_data_source.connection_status = "connected"

        mock_repository.list_by_project = AsyncMock(return_value=[mock_data_source])

        service = DataSourceService(repository=mock_repository)
        result = await service.list_finance_sources_for_project(self.PROJECT_ID)

        assert len(result) == 1
        assert result[0]["id"] == "22222222-2222-2222-2222-222222222222"
        assert result[0]["name"] == "Finance DB"
        assert result[0]["source_type"] == "postgresql"

    @pytest.mark.asyncio
    async def test_list_finance_sources_returns_empty_for_no_connections(self) -> None:
        mock_repository = AsyncMock()
        mock_repository.list_by_project = AsyncMock(return_value=[])

        service = DataSourceService(repository=mock_repository)
        result = await service.list_finance_sources_for_project(self.PROJECT_ID)

        assert result == []
