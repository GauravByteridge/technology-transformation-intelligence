"""
SDLC repository — database access layer for SDLC lifecycle entities.

Provides typed, parameterized access to sdlc_phases, sdlc_milestones,
and sdlc_deliverables tables in App_DB.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sdlc import SdlcDeliverable, SdlcMilestone, SdlcPhase
from app.repositories.base import BaseRepository


class SdlcRepository(BaseRepository[SdlcPhase]):
    """
    Encapsulates all database access for SDLC lifecycle entities.

    Manages queries across the phase → milestone → deliverable hierarchy.
    Inherits parameterized query patterns from BaseRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, SdlcPhase)

    async def list_phases_by_project(self, project_id: UUID) -> list[SdlcPhase]:
        """
        Retrieve all SDLC phases for a project, ordered by sequence.

        Args:
            project_id: UUID of the project.

        Returns:
            List of SdlcPhase instances ordered by sequence_order.
        """
        statement = (
            select(SdlcPhase)
            .where(SdlcPhase.project_id == project_id)
            .order_by(SdlcPhase.sequence_order)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_milestones_by_phase(self, phase_id: UUID) -> list[SdlcMilestone]:
        """
        Retrieve all milestones belonging to a specific phase.

        Args:
            phase_id: UUID of the SDLC phase.

        Returns:
            List of SdlcMilestone instances for the given phase.
        """
        statement = select(SdlcMilestone).where(
            SdlcMilestone.phase_id == phase_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_deliverables_by_milestone(
        self, milestone_id: UUID
    ) -> list[SdlcDeliverable]:
        """
        Retrieve all deliverables produced by a specific milestone.

        Args:
            milestone_id: UUID of the SDLC milestone.

        Returns:
            List of SdlcDeliverable instances for the given milestone.
        """
        statement = select(SdlcDeliverable).where(
            SdlcDeliverable.milestone_id == milestone_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
