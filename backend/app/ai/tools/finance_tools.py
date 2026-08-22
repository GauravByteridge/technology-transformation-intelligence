"""
Finance domain AI tools.

Provides the AI agent with finance-related data retrieval capabilities.
Tools call domain services only — never repositories or connectors directly.

WARNING: Do NOT add hardcoded financial numbers, project names, or demo data.
Demo Mode uses seeded data retrieved through service → repository → database.
"""

import structlog
from typing import Any
from uuid import UUID

from app.services.data_source_service import DataSourceService

logger = structlog.get_logger(__name__)


def create_query_project_finance(data_source_service: DataSourceService):
    """
    Factory that creates the query_project_finance tool function.

    Uses closure to inject the DataSourceService dependency, keeping
    the tool function signature clean for the agent invocation.

    Args:
        data_source_service: Injected DataSourceService for data access.

    Returns:
        Async tool function accepting project_id and returning finance data dict.
    """

    async def query_project_finance(project_id: UUID) -> dict[str, Any]:
        """
        Query finance-related data for a project.

        Retrieves connected finance data sources through
        DataSourceService → DataSourceRepository → App_DB.
        Returns structured info about what finance sources are connected
        and their status.

        Phase 1 will extend this to query actual financial metrics from
        connected external sources via connectors.

        Args:
            project_id: UUID of the project to query finance data for.

        Returns:
            Dict containing connected finance sources and source attribution label.
        """
        logger.info(
            "tool_query_project_finance_invoked",
            extra={"project_id": str(project_id)},
        )

        finance_sources = await data_source_service.list_finance_sources_for_project(
            project_id
        )

        return {
            "project_id": str(project_id),
            "connected_sources": finance_sources,
            "source_count": len(finance_sources),
            "source_label": "App_DB → data_sources, source_connections",
        }

    return query_project_finance
