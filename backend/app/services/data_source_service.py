"""
DataSource service — business logic layer for data source operations.

Accepts DataSourceRepository via constructor injection. Contains business
logic for querying connected data sources and delegates data access
to the repository layer.
"""

import structlog
from typing import Any
from uuid import UUID

from app.repositories.data_source_repository import DataSourceRepository

logger = structlog.get_logger(__name__)


class DataSourceService:
    """
    Business logic for data source operations.

    Dependencies are injected via constructor — never instantiated internally.
    """

    def __init__(self, repository: DataSourceRepository) -> None:
        """
        Initialize with a data source repository.

        Args:
            repository: DataSourceRepository instance for data access.
        """
        self._repository = repository

    async def list_finance_sources_for_project(
        self, project_id: UUID
    ) -> list[dict[str, Any]]:
        """
        List data sources connected to a project that contain finance data.

        Retrieves all data sources linked to the project. In Phase 0, all
        connected sources are returned as potential finance sources.
        Phase 1 will add source_type filtering and richer finance metadata.

        Args:
            project_id: UUID of the project to query.

        Returns:
            List of dicts describing connected data sources.
        """
        data_sources = await self._repository.list_by_project(project_id)

        logger.debug(
            "finance_sources_retrieved",
            extra={
                "project_id": str(project_id),
                "source_count": len(data_sources),
            },
        )

        return [
            {
                "id": str(source.id),
                "name": source.name,
                "source_type": source.source_type,
                "display_label": source.display_label,
                "connection_status": source.connection_status,
            }
            for source in data_sources
        ]
