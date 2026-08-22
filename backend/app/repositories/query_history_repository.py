"""
QueryHistory repository — database access layer for query history and saved query entities.

Provides typed, parameterized access to the query_history and saved_queries tables.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).

NOTE: query_history records are append-only — no update or delete operations are exposed.
This preserves the complete audit trail of AI query executions.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.query import QueryHistory, SavedQuery
from app.repositories.base import BaseRepository


class QueryHistoryRepository(BaseRepository[QueryHistory]):
    """
    Encapsulates all database access for QueryHistory and SavedQuery entities.

    QueryHistory is append-only — records are never updated or deleted to
    maintain a complete audit trail for traceability.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, QueryHistory)

    # --- QueryHistory (append-only) ---

    async def get_query_history(self, query_history_id: UUID) -> QueryHistory | None:
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
        Retrieve all query history records for a project, newest first.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of QueryHistory instances ordered by created_at descending.
        """
        statement = (
            select(QueryHistory)
            .where(QueryHistory.project_id == project_id)
            .order_by(QueryHistory.created_at.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create_query_history(self, entity: QueryHistory) -> QueryHistory:
        """
        Persist a new query history record (append-only).

        Args:
            entity: QueryHistory model instance to persist.

        Returns:
            The persisted QueryHistory with server-generated fields populated.
        """
        return await self._create(entity)

    # --- SavedQuery ---

    async def get_saved_query(self, saved_query_id: UUID) -> SavedQuery | None:
        """
        Retrieve a saved query by its primary key.

        Args:
            saved_query_id: UUID of the saved query.

        Returns:
            SavedQuery model instance, or None if not found.
        """
        result = await self._session.get(SavedQuery, saved_query_id)
        return result

    async def list_saved_by_project(self, project_id: UUID) -> list[SavedQuery]:
        """
        Retrieve all saved queries for a given project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of SavedQuery instances for the project.
        """
        statement = select(SavedQuery).where(
            SavedQuery.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create_saved_query(self, entity: SavedQuery) -> SavedQuery:
        """
        Persist a new saved query to the database.

        Args:
            entity: SavedQuery model instance to persist.

        Returns:
            The persisted SavedQuery with server-generated fields populated.
        """
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete_saved_query(self, saved_query_id: UUID) -> bool:
        """
        Delete a saved query by its primary key.

        Args:
            saved_query_id: UUID of the saved query to delete.

        Returns:
            True if the saved query was deleted, False if not found.
        """
        from sqlalchemy import delete

        statement = delete(SavedQuery).where(SavedQuery.id == saved_query_id)
        result = await self._session.execute(statement)
        return result.rowcount > 0  # type: ignore[union-attr]
