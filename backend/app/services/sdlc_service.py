"""
SDLC service — business logic layer for SDLC lifecycle operations.

Provides retrieval of SDLC phases with their milestones and deliverables
for a given project. Accepts SdlcRepository via constructor injection.

No complex business logic — the service assembles the phase → milestone →
deliverable hierarchy into a response dictionary.
"""

import structlog
from uuid import UUID

from app.repositories.sdlc_repository import SdlcRepository

logger = structlog.get_logger(__name__)


class SdlcService:
    """
    Business logic for SDLC lifecycle operations.

    Retrieves phases ordered by sequence_order from the repository and
    assembles them with their milestones and deliverables into a response.
    Dependencies injected via constructor.
    """

    def __init__(self, repository: SdlcRepository) -> None:
        """
        Initialize with an SDLC repository.

        Args:
            repository: SdlcRepository instance for data access.
        """
        self._repository = repository

    async def get_project_sdlc(self, project_id: UUID) -> dict:
        """
        Retrieve SDLC lifecycle data for a project.

        Fetches phases ordered by sequence_order, with milestones and
        deliverables for each phase assembled into a hierarchical structure.

        Args:
            project_id: UUID of the project to retrieve SDLC data for.

        Returns:
            Dictionary containing project_id and a list of phases, each
            with their milestones and deliverables.
        """
        phases = await self._repository.list_phases_by_project(project_id)

        phases_data = []
        for phase in phases:
            milestones = await self._repository.list_milestones_by_phase(phase.id)

            milestones_data = []
            for milestone in milestones:
                deliverables = await self._repository.list_deliverables_by_milestone(
                    milestone.id
                )
                milestones_data.append(
                    {
                        "id": milestone.id,
                        "name": milestone.name,
                        "description": milestone.description,
                        "planned_date": milestone.planned_date,
                        "actual_date": milestone.actual_date,
                        "status": milestone.status,
                        "deliverables": [
                            {
                                "id": deliverable.id,
                                "name": deliverable.name,
                                "description": deliverable.description,
                                "status": deliverable.status,
                                "owner": deliverable.owner,
                                "due_date": deliverable.due_date,
                                "completion_date": deliverable.completion_date,
                            }
                            for deliverable in deliverables
                        ],
                    }
                )

            phases_data.append(
                {
                    "id": phase.id,
                    "phase_name": phase.phase_name,
                    "sequence_order": phase.sequence_order,
                    "status": phase.status,
                    "planned_start_date": phase.planned_start_date,
                    "planned_end_date": phase.planned_end_date,
                    "actual_start_date": phase.actual_start_date,
                    "actual_end_date": phase.actual_end_date,
                    "milestones": milestones_data,
                }
            )

        logger.debug(
            "project_sdlc_retrieved",
            project_id=str(project_id),
            phase_count=len(phases_data),
        )

        return {
            "project_id": project_id,
            "phases": phases_data,
        }
