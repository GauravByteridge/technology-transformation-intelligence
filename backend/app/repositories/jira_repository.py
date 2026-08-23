"""
JIRA repository — database access layer for sprints and issues.

Provides typed, parameterized access to the sprints and jira_issues tables.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from datetime import date
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jira import JiraIssue, Sprint
from app.repositories.base import BaseRepository

# Statuses considered "open" for counting purposes
_OPEN_STATUSES = ("To Do", "In Progress", "Blocked")


class JiraRepository(BaseRepository[JiraIssue]):
    """
    Encapsulates all database access for JIRA issues and sprints.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, JiraIssue)

    async def list_issues_by_project(self, project_id: UUID) -> list[JiraIssue]:
        """
        Retrieve all JIRA issues for a given project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of JiraIssue instances belonging to the project.
        """
        statement = select(JiraIssue).where(JiraIssue.project_id == project_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_sprints_by_project(self, project_id: UUID) -> list[Sprint]:
        """
        Retrieve all sprints for a given project, ordered by sprint number.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of Sprint instances ordered by sprint_number ascending.
        """
        statement = (
            select(Sprint)
            .where(Sprint.project_id == project_id)
            .order_by(Sprint.sprint_number)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def count_open_issues(self, project_id: UUID) -> int:
        """
        Count issues with open statuses for a project.

        Open statuses: "To Do", "In Progress", "Blocked".

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            Number of open issues.
        """
        statement = (
            select(sa.func.count())
            .select_from(JiraIssue)
            .where(
                JiraIssue.project_id == project_id,
                JiraIssue.status.in_(_OPEN_STATUSES),
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one()

    async def count_overdue_issues(self, project_id: UUID) -> int:
        """
        Count issues that are past their due date and not yet done.

        An issue is overdue when due_date < today AND status != "Done".

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            Number of overdue issues.
        """
        statement = (
            select(sa.func.count())
            .select_from(JiraIssue)
            .where(
                JiraIssue.project_id == project_id,
                JiraIssue.due_date < date.today(),
                JiraIssue.status != "Done",
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one()
