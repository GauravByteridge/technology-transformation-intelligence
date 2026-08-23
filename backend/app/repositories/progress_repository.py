"""
Progress repository — database access layer for project progress snapshot entities.

Provides typed, parameterized access to the project_progress_snapshots table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.progress import ProjectProgressSnapshot
from app.repositories.base import BaseRepository


class ProgressRepository(BaseRepository[ProjectProgressSnapshot]):
    """
    Encapsulates all database access for ProjectProgressSnapshot entities.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, ProjectProgressSnapshot)

    async def list_snapshots_by_project(
        self, project_id: UUID
    ) -> list[ProjectProgressSnapshot]:
        """
        Retrieve all progress snapshots for a project, ordered by snapshot date.

        Args:
            project_id: UUID of the project to retrieve snapshots for.

        Returns:
            List of ProjectProgressSnapshot instances ordered by snapshot_date ascending.
        """
        statement = (
            select(ProjectProgressSnapshot)
            .where(ProjectProgressSnapshot.project_id == project_id)
            .order_by(ProjectProgressSnapshot.snapshot_date)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_most_recent_snapshot(
        self, project_id: UUID
    ) -> ProjectProgressSnapshot | None:
        """
        Retrieve the most recent progress snapshot for a project.

        Args:
            project_id: UUID of the project to retrieve the latest snapshot for.

        Returns:
            The most recent ProjectProgressSnapshot, or None if no snapshots exist.
        """
        statement = (
            select(ProjectProgressSnapshot)
            .where(ProjectProgressSnapshot.project_id == project_id)
            .order_by(ProjectProgressSnapshot.snapshot_date.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalars().first()
