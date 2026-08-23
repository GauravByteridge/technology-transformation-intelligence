"""
Audit Finding repository — database access layer for audit finding entities.

Provides typed, parameterized access to the audit_findings table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_finding import AuditFinding
from app.repositories.base import BaseRepository

# Statuses considered "open" for counting purposes
_OPEN_STATUSES = ("Open", "In Progress")


class AuditFindingRepository(BaseRepository[AuditFinding]):
    """
    Encapsulates all database access for AuditFinding entities.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, AuditFinding)

    async def list_findings_by_project(self, project_id: UUID) -> list[AuditFinding]:
        """
        Retrieve all audit findings for a given project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of AuditFinding instances for the project.
        """
        statement = select(AuditFinding).where(
            AuditFinding.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def count_open_findings(self, project_id: UUID) -> int:
        """
        Count audit findings that are still open for a given project.

        Open findings have status IN ("Open", "In Progress").

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            Integer count of open findings.
        """
        statement = (
            select(func.count())
            .select_from(AuditFinding)
            .where(
                AuditFinding.project_id == project_id,
                AuditFinding.status.in_(_OPEN_STATUSES),
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one()
