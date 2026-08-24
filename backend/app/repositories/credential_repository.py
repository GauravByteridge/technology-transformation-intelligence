"""
Credential repository — database access layer for data_source_credentials.

Provides typed, parameterized access to the data_source_credentials table.
Credential records store ONLY vault references — never raw secrets.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source_credential import DataSourceCredential
from app.repositories.base import BaseRepository


class CredentialRepository(BaseRepository[DataSourceCredential]):
    """Encapsulates all database access for DataSourceCredential entities."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, DataSourceCredential)

    async def get_by_data_source(self, data_source_id: UUID) -> list[DataSourceCredential]:
        """
        Retrieve all credential records for a data source.

        Args:
            data_source_id: UUID of the data source.

        Returns:
            List of DataSourceCredential records for the given data source.
        """
        statement = select(DataSourceCredential).where(
            DataSourceCredential.data_source_id == data_source_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create_credential(self, credential: DataSourceCredential) -> DataSourceCredential:
        """
        Persist a new credential record.

        Args:
            credential: DataSourceCredential model instance to persist.

        Returns:
            The persisted entity with server-generated fields populated.
        """
        return await self._create(credential)

    async def delete_by_data_source(self, data_source_id: UUID) -> int:
        """
        Delete all credential records for a data source.

        Args:
            data_source_id: UUID of the data source.

        Returns:
            Number of records deleted.
        """
        from sqlalchemy import delete as sa_delete

        statement = sa_delete(DataSourceCredential).where(
            DataSourceCredential.data_source_id == data_source_id
        )
        result = await self._session.execute(statement)
        return result.rowcount  # type: ignore[union-attr]
