"""
Risk repository — database access layer for project risk entities.

Provides typed, parameterized access to the project_risks table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk import ProjectRisk
from app.repositories.base import BaseRepository


class RiskRepository(BaseRepository[ProjectRisk]):
    """
    Encapsulates all database access for ProjectRisk entities.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, ProjectRisk)

    async def list_risks_by_project(self, project_id: UUID) -> list[ProjectRisk]:
        """
        Retrieve all risk records for a given project.

        Args:
            project_id: UUID of the project to retrieve risks for.

        Returns:
            List of ProjectRisk model instances for the project.
        """
        statement = select(ProjectRisk).where(
            ProjectRisk.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def count_open_risks(self, project_id: UUID) -> int:
        """
        Count risks with status 'Open' for a given project.

        Args:
            project_id: UUID of the project to count open risks for.

        Returns:
            Number of open risks for the project.
        """
        statement = (
            select(func.count(ProjectRisk.id))
            .where(ProjectRisk.project_id == project_id)
            .where(ProjectRisk.status == "Open")
        )
        result = await self._session.execute(statement)
        count = result.scalar()
        return count if count is not None else 0
