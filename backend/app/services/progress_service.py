"""
Progress service — business logic layer for project progress operations.

Provides retrieval of progress snapshots and derivation of the current
progress percentage from the most recent snapshot. Accepts ProgressRepository
via constructor injection.
"""

import structlog
from uuid import UUID

from app.models.progress import ProjectProgressSnapshot
from app.repositories.progress_repository import ProgressRepository

logger = structlog.get_logger(__name__)


class ProgressService:
    """
    Business logic for project progress operations.

    Retrieves progress snapshots from the repository and derives the
    current progress percentage from the most recent snapshot date.
    Dependencies injected via constructor.
    """

    def __init__(self, repository: ProgressRepository) -> None:
        """
        Initialize with a progress repository.

        Args:
            repository: ProgressRepository instance for data access.
        """
        self._repository = repository

    async def get_project_progress(self, project_id: UUID) -> dict:
        """
        Retrieve progress snapshot data for a project.

        Fetches all snapshots ordered by snapshot_date and derives the
        current progress percentage from the most recent snapshot.

        Args:
            project_id: UUID of the project to retrieve progress data for.

        Returns:
            Dictionary containing project_id, snapshots list, and derived
            current progress_percentage.
        """
        snapshots = await self._repository.list_snapshots_by_project(project_id)
        progress_percentage = self.derive_progress_percentage(snapshots)

        logger.debug(
            "project_progress_retrieved",
            project_id=str(project_id),
            snapshot_count=len(snapshots),
            progress_percentage=progress_percentage,
        )

        return {
            "project_id": project_id,
            "snapshots": [
                {
                    "id": snapshot.id,
                    "snapshot_date": snapshot.snapshot_date,
                    "planned_progress_percentage": snapshot.planned_progress_percentage,
                    "actual_progress_percentage": snapshot.actual_progress_percentage,
                }
                for snapshot in snapshots
            ],
            "progress_percentage": progress_percentage,
        }

    def derive_progress_percentage(
        self, snapshots: list[ProjectProgressSnapshot]
    ) -> int:
        """
        Derive current progress percentage from the most recent snapshot.

        Returns the actual_progress_percentage of the snapshot with the
        maximum snapshot_date. If the snapshot list is empty, returns 0.

        Args:
            snapshots: List of ProjectProgressSnapshot instances.

        Returns:
            Integer progress percentage (0–100), or 0 if no snapshots exist.
        """
        if not snapshots:
            return 0

        most_recent = max(snapshots, key=lambda s: s.snapshot_date)
        return most_recent.actual_progress_percentage
