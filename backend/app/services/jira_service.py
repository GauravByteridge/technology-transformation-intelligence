"""
JIRA service — business logic for JIRA sprint and issue metrics.

Provides pure business calculations for open issues count, overdue count,
and completion percentage. All DB access is delegated to JiraRepository.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

import structlog

from app.models.jira import JiraIssue, Sprint
from app.repositories.jira_repository import JiraRepository

logger = structlog.get_logger(__name__)

# Statuses considered "open" — excludes only "Done"
_OPEN_STATUSES = frozenset({"To Do", "In Progress", "Blocked"})


class JiraService:
    """
    Business logic for JIRA sprint and issue data.

    Dependencies are injected via constructor.
    Calculation methods are pure functions operating on in-memory lists.
    """

    def __init__(self, repository: JiraRepository) -> None:
        """
        Initialize with a JIRA repository.

        Args:
            repository: JiraRepository instance for data access.
        """
        self._repository = repository

    async def get_project_jira(self, project_id: UUID) -> dict:
        """
        Retrieve sprints and issues for a project with computed metrics.

        Args:
            project_id: UUID of the project.

        Returns:
            Dictionary containing sprints, issues, and computed metrics.
        """
        sprints: list[Sprint] = await self._repository.list_sprints_by_project(
            project_id
        )
        issues: list[JiraIssue] = await self._repository.list_issues_by_project(
            project_id
        )

        open_count = self.calculate_open_issues_count(issues)
        overdue_count = self.calculate_overdue_count(issues)
        completion_pct = self.calculate_completion_percentage(issues)

        logger.debug(
            "jira_metrics_calculated",
            project_id=str(project_id),
            total_issues=len(issues),
            open_count=open_count,
            overdue_count=overdue_count,
            completion_percentage=str(completion_pct),
        )

        return {
            "sprints": sprints,
            "issues": issues,
            "open_issues_count": open_count,
            "overdue_issues_count": overdue_count,
            "completion_percentage": completion_pct,
        }

    def calculate_open_issues_count(self, issues: list[JiraIssue]) -> int:
        """
        Count issues with status IN ("To Do", "In Progress", "Blocked").

        This is DISTINCT from overdue count. Open means not Done.

        Args:
            issues: List of JiraIssue instances.

        Returns:
            Number of open issues.
        """
        return sum(1 for issue in issues if issue.status in _OPEN_STATUSES)

    def calculate_overdue_count(self, issues: list[JiraIssue]) -> int:
        """
        Count issues past their due date that are not yet done.

        An issue is overdue when due_date < today AND status != "Done".
        A null due_date means the issue is NOT overdue.

        This is DISTINCT from open count — an issue can be open but not
        overdue (no due_date or future due_date), or overdue and open.

        Args:
            issues: List of JiraIssue instances.

        Returns:
            Number of overdue issues.
        """
        today = date.today()
        return sum(
            1
            for issue in issues
            if issue.due_date is not None
            and issue.due_date < today
            and issue.status != "Done"
        )

    def calculate_completion_percentage(self, issues: list[JiraIssue]) -> Decimal:
        """
        Calculate percentage of issues with status "Done".

        Args:
            issues: List of JiraIssue instances.

        Returns:
            Percentage as Decimal (0–100). Returns Decimal("0") for empty list.
        """
        if not issues:
            return Decimal("0")
        done_count = sum(1 for issue in issues if issue.status == "Done")
        return (Decimal(done_count) * Decimal(100)) / Decimal(len(issues))
