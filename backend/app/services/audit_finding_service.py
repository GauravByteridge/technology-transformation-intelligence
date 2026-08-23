"""
Audit Finding service — business logic for audit finding operations.

Implements overdue detection as a derived state: an audit finding is overdue
when status IN ("Open", "In Progress") AND target_remediation_date is not None
AND target_remediation_date < today. This is NOT a stored status value.
"""

from datetime import date
from uuid import UUID

import structlog

from app.models.audit_finding import AuditFinding
from app.repositories.audit_finding_repository import AuditFindingRepository

logger = structlog.get_logger(__name__)

# Statuses that qualify for overdue evaluation
_OVERDUE_ELIGIBLE_STATUSES = ("Open", "In Progress")


class AuditFindingService:
    """
    Business logic for audit finding operations.

    Provides overdue detection as a derived condition — findings are considered
    overdue when they have an open status AND the target remediation date has passed.
    """

    def __init__(self, repository: AuditFindingRepository) -> None:
        """
        Initialize with an audit finding repository.

        Args:
            repository: AuditFindingRepository instance for data access.
        """
        self._repository = repository

    async def get_project_audit(self, project_id: UUID) -> dict:
        """
        Retrieve all audit findings for a project with overdue metadata.

        Args:
            project_id: UUID of the project to retrieve findings for.

        Returns:
            Dictionary containing findings list and overdue count.
        """
        findings = await self._repository.list_findings_by_project(project_id)
        overdue_count = self.count_overdue_findings(findings)

        logger.debug(
            "project_audit_retrieved",
            project_id=str(project_id),
            total_findings=len(findings),
            overdue_count=overdue_count,
        )

        return {
            "findings": findings,
            "overdue_count": overdue_count,
        }

    def is_overdue(self, finding: AuditFinding) -> bool:
        """
        Determine if an audit finding is overdue (derived state).

        An audit finding is overdue when ALL conditions are met:
        1. status is in ("Open", "In Progress")
        2. target_remediation_date is not None
        3. target_remediation_date < today

        Args:
            finding: AuditFinding instance to evaluate.

        Returns:
            True if the finding meets all overdue conditions.
        """
        if finding.status not in _OVERDUE_ELIGIBLE_STATUSES:
            return False

        if finding.target_remediation_date is None:
            return False

        return finding.target_remediation_date < date.today()

    def count_overdue_findings(self, findings: list[AuditFinding]) -> int:
        """
        Count the number of overdue findings in a list.

        Uses the is_overdue logic to evaluate each finding.

        Args:
            findings: List of AuditFinding instances to evaluate.

        Returns:
            Integer count of findings that are overdue.
        """
        return sum(1 for finding in findings if self.is_overdue(finding))
