"""
Risk service — business logic for project risk domain operations.

Provides risk retrieval and open-risk counting for the Project 360 view,
risk dashboards, and AI queries. All DB access is delegated to RiskRepository.
"""

from uuid import UUID

import structlog

from app.models.risk import ProjectRisk
from app.repositories.risk_repository import RiskRepository

logger = structlog.get_logger(__name__)

# Status value indicating an open (unmitigated) risk
_OPEN_STATUS = "Open"


class RiskService:
    """
    Business logic for project risk data.

    Dependencies are injected via constructor.
    Calculation methods are pure functions operating on in-memory lists.
    """

    def __init__(self, repository: RiskRepository) -> None:
        """
        Initialize with a risk repository.

        Args:
            repository: RiskRepository instance for data access.
        """
        self._repository = repository

    async def get_project_risks(self, project_id: UUID) -> dict:
        """
        Retrieve risks for a project with the open count metric.

        Args:
            project_id: UUID of the project.

        Returns:
            Dictionary containing risks list and open_risks_count.
        """
        risks: list[ProjectRisk] = await self._repository.list_risks_by_project(
            project_id
        )

        open_count = self.calculate_open_risks_count(risks)

        logger.debug(
            "project_risks_retrieved",
            project_id=str(project_id),
            total_risks=len(risks),
            open_risks_count=open_count,
        )

        return {
            "risks": risks,
            "open_risks_count": open_count,
        }

    def calculate_open_risks_count(self, risks: list[ProjectRisk]) -> int:
        """
        Count risks with status == "Open".

        A risk is considered open when its status is exactly "Open".
        "Mitigated" and "Closed" statuses are excluded.

        Args:
            risks: List of ProjectRisk instances.

        Returns:
            Number of open risks.
        """
        return sum(1 for risk in risks if risk.status == _OPEN_STATUS)
