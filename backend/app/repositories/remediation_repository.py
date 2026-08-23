"""
Remediation repository — database access layer for remediation item entities.

Provides typed, parameterized access to the remediation_items table.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remediation import RemediationItem
from app.repositories.base import BaseRepository

# Statuses considered "open" for counting purposes
_OPEN_STATUSES = ("Open", "In Progress")


class RemediationRepository(BaseRepository[RemediationItem]):
    """
    Encapsulates all database access for RemediationItem entities.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, RemediationItem)

    async def list_items_by_project(self, project_id: UUID) -> list[RemediationItem]:
        """
        Retrieve all remediation items for a given project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of RemediationItem instances belonging to the project.
        """
        statement = select(RemediationItem).where(
            RemediationItem.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def count_open_items(self, project_id: UUID) -> int:
        """
        Count remediation items with open statuses for a project.

        Open statuses: "Open", "In Progress".

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            Number of open remediation items.
        """
        statement = (
            select(sa.func.count())
            .select_from(RemediationItem)
            .where(
                RemediationItem.project_id == project_id,
                RemediationItem.status.in_(_OPEN_STATUSES),
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one()
