"""
Health KPI repository — database access layer for project health KPI entities.

Provides typed, parameterized access to the project_health_kpis table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_kpi import ProjectHealthKpi
from app.repositories.base import BaseRepository


class HealthKpiRepository(BaseRepository[ProjectHealthKpi]):
    """
    Encapsulates all database access for ProjectHealthKpi entities.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, ProjectHealthKpi)

    async def get_by_project(self, project_id: UUID) -> ProjectHealthKpi | None:
        """
        Retrieve the health KPI record for a given project.

        Args:
            project_id: UUID of the project to look up KPIs for.

        Returns:
            ProjectHealthKpi model instance, or None if no KPI record exists.
        """
        statement = select(ProjectHealthKpi).where(
            ProjectHealthKpi.project_id == project_id
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def upsert(self, kpi: ProjectHealthKpi) -> ProjectHealthKpi:
        """
        Insert or update a project health KPI record.

        Uses session.merge() to handle both insert (new project_id) and
        update (existing project_id) cases transparently.

        Args:
            kpi: ProjectHealthKpi model instance to persist or update.

        Returns:
            The persisted/updated ProjectHealthKpi with server-generated
            fields populated.
        """
        merged = await self._session.merge(kpi)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def list_all(self) -> list[ProjectHealthKpi]:
        """
        Retrieve all project health KPI records.

        Returns:
            List of all ProjectHealthKpi model instances.
        """
        return await self._list_all()
