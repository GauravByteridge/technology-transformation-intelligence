"""
QueryHistory repository — database access layer for query history entities.

Phase 0: Interface stub with minimal method signatures.
Full implementation deferred to AI query feature phase.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.query import QueryHistory
from app.repositories.base import BaseRepository


class QueryHistoryRepository(BaseRepository[QueryHistory]):
    """
    Encapsulates all database access for QueryHistory entities.

    Phase 0: Stub with interface definitions.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, QueryHistory)

    async def get_query(self, query_history_id: UUID) -> QueryHistory | None:
        """
        Retrieve a query history record by its primary key.

        Args:
            query_history_id: UUID of the query history record.

        Returns:
            QueryHistory model instance, or None if not found.
        """
        return await self._get_by_id(query_history_id)

    async def list_by_project(self, project_id: UUID) -> list[QueryHistory]:
        """
        Retrieve all query history records for a given project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of QueryHistory instances for the project.
        """
        raise NotImplementedError(
            "QueryHistoryRepository.list_by_project — deferred to AI query feature phase"
        )
