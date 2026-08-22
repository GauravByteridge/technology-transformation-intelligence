"""
DataSource repository — database access layer for data source entities.

Provides typed, parameterized access to the data_sources table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import DataSource
from app.repositories.base import BaseRepository


class DataSourceRepository(BaseRepository[DataSource]):
    """
    Encapsulates all database access for DataSource entities.

    Inherits parameterized query patterns from BaseRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, DataSource)

    async def get_data_source(self, data_source_id: UUID) -> DataSource | None:
        """
        Retrieve a data source by its primary key.

        Args:
            data_source_id: UUID of the data source to retrieve.

        Returns:
            DataSource model instance, or None if not found.
        """
        return await self._get_by_id(data_source_id)

    async def list_data_sources(self) -> list[DataSource]:
        """
        Retrieve all data sources.

        Returns:
            List of all DataSource model instances.
        """
        return await self._list_all()

    async def list_by_project(self, project_id: UUID) -> list[DataSource]:
        """
        Retrieve all data sources connected to a specific project.

        Joins through source_connections to find data sources linked
        to the given project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of DataSource instances connected to the project.
        """
        from app.models.data_source import SourceConnection

        statement = (
            select(DataSource)
            .join(
                SourceConnection,
                SourceConnection.data_source_id == DataSource.id,
            )
            .where(SourceConnection.project_id == project_id)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create_data_source(self, entity: DataSource) -> DataSource:
        """
        Persist a new data source to the database.

        Args:
            entity: DataSource model instance to persist.

        Returns:
            The persisted DataSource with server-generated fields populated.
        """
        return await self._create(entity)

    async def update_data_source(
        self, data_source_id: UUID, updates: dict
    ) -> DataSource | None:
        """
        Apply partial updates to an existing data source.

        Args:
            data_source_id: UUID of the data source to update.
            updates: Dictionary of field names to new values.

        Returns:
            Updated DataSource instance, or None if not found.
        """
        data_source = await self._get_by_id(data_source_id)
        if data_source is None:
            return None

        for field, value in updates.items():
            if hasattr(data_source, field):
                setattr(data_source, field, value)

        await self._session.flush()
        await self._session.refresh(data_source)
        return data_source

    async def delete_data_source(self, data_source_id: UUID) -> bool:
        """
        Delete a data source by its primary key.

        Args:
            data_source_id: UUID of the data source to delete.

        Returns:
            True if the data source was deleted, False if not found.
        """
        return await self._delete_by_id(data_source_id)
