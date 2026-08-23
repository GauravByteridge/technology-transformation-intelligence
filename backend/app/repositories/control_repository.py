"""
Control repository — database access layer for IT control and control assessment entities.

Provides typed, parameterized access to the it_controls and control_assessments
tables in App_DB. All queries use SQLAlchemy ORM with bound parameters
(inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.it_control import ControlAssessment, ItControl
from app.repositories.base import BaseRepository


class ControlRepository(BaseRepository[ItControl]):
    """
    Encapsulates all database access for ItControl and ControlAssessment entities.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, ItControl)

    async def list_controls(self) -> list[ItControl]:
        """
        Retrieve all IT controls.

        Returns:
            List of all ItControl model instances.
        """
        return await self._list_all()

    async def list_assessments_by_project(self, project_id: UUID) -> list[ControlAssessment]:
        """
        Retrieve all control assessments for a given project.

        Args:
            project_id: UUID of the project to filter assessments by.

        Returns:
            List of ControlAssessment instances for the project.
        """
        statement = select(ControlAssessment).where(
            ControlAssessment.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
