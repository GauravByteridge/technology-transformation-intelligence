"""
Remediation service — business logic for remediation item operations.

Implements overdue detection as a derived state: a remediation item is overdue
when status IN ("Open", "In Progress") AND due_date < today. This is NOT a
stored status value.
"""

from datetime import date
from uuid import UUID

import structlog

from app.models.remediation import RemediationItem
from app.repositories.remediation_repository import RemediationRepository

logger = structlog.get_logger(__name__)

# Statuses that qualify for overdue evaluation
_OVERDUE_ELIGIBLE_STATUSES = ("Open", "In Progress")


class RemediationService:
    """
    Business logic for remediation item operations.

    Provides overdue detection as a derived condition — items are considered
    overdue when they have an open status AND the due date has passed.
    """

    def __init__(self, repository: RemediationRepository) -> None:
        """
        Initialize with a remediation repository.

        Args:
            repository: RemediationRepository instance for data access.
        """
        self._repository = repository

    async def get_project_remediation(self, project_id: UUID) -> dict:
        """
        Retrieve all remediation items for a project with overdue metadata.

        Args:
            project_id: UUID of the project to retrieve items for.

        Returns:
            Dictionary containing items list and overdue count.
        """
        items = await self._repository.list_items_by_project(project_id)
        overdue_count = self.count_overdue_items(items)

        logger.debug(
            "project_remediation_retrieved",
            project_id=str(project_id),
            total_items=len(items),
            overdue_count=overdue_count,
        )

        return {
            "items": items,
            "overdue_count": overdue_count,
        }

    def is_overdue(self, item: RemediationItem) -> bool:
        """
        Determine if a remediation item is overdue (derived state).

        A remediation item is overdue when ALL conditions are met:
        1. status is in ("Open", "In Progress")
        2. due_date < today

        Args:
            item: RemediationItem instance to evaluate.

        Returns:
            True if the item meets all overdue conditions.
        """
        if item.status not in _OVERDUE_ELIGIBLE_STATUSES:
            return False

        return item.due_date < date.today()

    def count_overdue_items(self, items: list[RemediationItem]) -> int:
        """
        Count the number of overdue items in a list.

        Uses the is_overdue logic to evaluate each item.

        Args:
            items: List of RemediationItem instances to evaluate.

        Returns:
            Integer count of items that are overdue.
        """
        return sum(1 for item in items if self.is_overdue(item))
