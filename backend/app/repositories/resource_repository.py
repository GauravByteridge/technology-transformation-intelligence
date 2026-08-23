"""
Resource repository — database access layer for resource management entities.

Provides typed, parameterized access to resource_allocations, resource_utilization,
and resource_forecasts tables in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource import (
    ResourceAllocation,
    ResourceForecast,
    ResourceUtilization,
)
from app.repositories.base import BaseRepository


class ResourceRepository(BaseRepository[ResourceAllocation]):
    """
    Encapsulates all database access for resource management entities.

    Covers allocations, utilization tracking, and demand/capacity forecasts.
    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, ResourceAllocation)

    async def list_allocations_by_project(
        self, project_id: UUID
    ) -> list[ResourceAllocation]:
        """
        Retrieve all resource allocations for a given project.

        Args:
            project_id: UUID of the project to filter allocations by.

        Returns:
            List of ResourceAllocation instances for the project.
        """
        statement = select(ResourceAllocation).where(
            ResourceAllocation.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_utilization_by_members(
        self, member_ids: list[UUID], year_month: str
    ) -> list[ResourceUtilization]:
        """
        Retrieve utilization records for specified team members in a given month.

        Args:
            member_ids: List of team member UUIDs to filter by.
            year_month: Month string in "YYYY-MM" format.

        Returns:
            List of ResourceUtilization instances matching the criteria.
        """
        statement = select(ResourceUtilization).where(
            ResourceUtilization.team_member_id.in_(member_ids),
            ResourceUtilization.year_month == year_month,
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_forecasts_by_project(
        self, project_id: UUID
    ) -> list[ResourceForecast]:
        """
        Retrieve resource forecasts for a given project, ordered by month.

        Args:
            project_id: UUID of the project to filter forecasts by.

        Returns:
            List of ResourceForecast instances ordered by year_month ascending.
        """
        statement = (
            select(ResourceForecast)
            .where(ResourceForecast.project_id == project_id)
            .order_by(ResourceForecast.year_month)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_most_recent_utilization_month(self) -> str | None:
        """
        Get the most recent year_month value from utilization records.

        Returns:
            The latest "YYYY-MM" string, or None if no records exist.
        """
        statement = select(sa.func.max(ResourceUtilization.year_month))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
