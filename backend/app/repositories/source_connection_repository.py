"""
SourceConnection repository — manages project-to-data-source relationships.

Provides typed, parameterized access to the source_connections table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import SourceConnection
from app.repositories.base import BaseRepository


class SourceConnectionRepository(BaseRepository[SourceConnection]):
    """
    Encapsulates all database access for SourceConnection entities.

    SourceConnections link data sources to projects, enabling multi-source
    project contexts for AI queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, SourceConnection)

    async def list_sources_for_project(
        self, project_id: UUID
    ) -> list[SourceConnection]:
        """
        Retrieve all source connections for a given project.

        Args:
            project_id: UUID of the project whose connections to retrieve.

        Returns:
            List of SourceConnection instances linked to the project.
        """
        statement = select(SourceConnection).where(
            SourceConnection.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
