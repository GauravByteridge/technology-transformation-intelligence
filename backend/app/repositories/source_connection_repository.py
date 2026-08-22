"""
SourceConnection repository — manages project-to-data-source relationships.

Provides typed, parameterized access to the source_connections table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.datasource_errors import DuplicateSourceConnectionError
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

    async def list_by_project(self, project_id: UUID) -> list[SourceConnection]:
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

    async def create_connection(self, entity: SourceConnection) -> SourceConnection:
        """
        Persist a new source connection, enforcing uniqueness per project+data_source.

        Catches IntegrityError from the UNIQUE(project_id, data_source_id) constraint
        and raises DuplicateSourceConnectionError for clear domain-level handling.

        Args:
            entity: SourceConnection model instance to persist.

        Returns:
            The persisted SourceConnection with server-generated fields populated.

        Raises:
            DuplicateSourceConnectionError: If the project already has a connection
                to the same data source.
        """
        try:
            return await self._create(entity)
        except IntegrityError:
            await self._session.rollback()
            raise DuplicateSourceConnectionError(
                project_id=str(entity.project_id),
                data_source_id=str(entity.data_source_id),
            )

    async def delete_connection(
        self, project_id: UUID, data_source_id: UUID
    ) -> bool:
        """
        Delete a source connection by its composite key (project_id, data_source_id).

        Args:
            project_id: UUID of the project.
            data_source_id: UUID of the data source.

        Returns:
            True if a connection was deleted, False if not found.
        """
        statement = delete(SourceConnection).where(
            and_(
                SourceConnection.project_id == project_id,
                SourceConnection.data_source_id == data_source_id,
            )
        )
        result = await self._session.execute(statement)
        return result.rowcount > 0  # type: ignore[union-attr]

    # Keep backward-compatible alias
    async def list_sources_for_project(
        self, project_id: UUID
    ) -> list[SourceConnection]:
        """Alias for list_by_project — preserves backward compatibility."""
        return await self.list_by_project(project_id)
