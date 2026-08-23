"""
Control service — business logic for IT control and compliance operations.

Computes compliance percentage from control assessments: the ratio of assessments
with compliance_status "Compliant" to total assessments for a project,
expressed as an integer percentage.
"""

from uuid import UUID

import structlog

from app.models.it_control import ControlAssessment
from app.repositories.control_repository import ControlRepository

logger = structlog.get_logger(__name__)

# The compliance status value that counts toward compliance percentage
_COMPLIANT_STATUS = "Compliant"


class ControlService:
    """
    Business logic for IT control compliance operations.

    Retrieves control assessments per project and computes the compliance
    percentage as int((compliant_count / total_count) * 100).
    """

    def __init__(self, repository: ControlRepository) -> None:
        """
        Initialize with a control repository.

        Args:
            repository: ControlRepository instance for data access.
        """
        self._repository = repository

    async def get_project_controls(self, project_id: UUID) -> dict:
        """
        Retrieve control assessments for a project and compute compliance percentage.

        Args:
            project_id: UUID of the project to retrieve assessments for.

        Returns:
            Dictionary containing assessments list and compliance_percentage.
        """
        assessments = await self._repository.list_assessments_by_project(project_id)
        compliance_percentage = self.calculate_compliance_percentage(assessments)

        logger.debug(
            "project_controls_retrieved",
            project_id=str(project_id),
            total_assessments=len(assessments),
            compliance_percentage=compliance_percentage,
        )

        return {
            "assessments": assessments,
            "compliance_percentage": compliance_percentage,
        }

    def calculate_compliance_percentage(self, assessments: list[ControlAssessment]) -> int:
        """
        Calculate the IT control compliance percentage for a set of assessments.

        Formula: int((count of "Compliant" assessments / total assessments) * 100)
        Returns 0 for an empty list.

        Args:
            assessments: List of ControlAssessment instances to evaluate.

        Returns:
            Integer percentage (0–100) of assessments that are "Compliant".
        """
        if not assessments:
            return 0

        compliant_count = sum(
            1 for a in assessments if a.compliance_status == _COMPLIANT_STATUS
        )

        return int((compliant_count / len(assessments)) * 100)
