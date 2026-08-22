"""
Project service — business logic layer for project operations.

Accepts ProjectRepository via constructor injection. Contains business
logic and delegates data access to the repository layer.
"""

import structlog
from uuid import UUID

from app.errors.project_errors import ProjectNotFoundError
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectResponse

logger = structlog.get_logger(__name__)


class ProjectService:
    """
    Business logic for project operations.

    Dependencies are injected via constructor — never instantiated internally.
    This makes the service testable with mock repositories.
    """

    def __init__(self, repository: ProjectRepository) -> None:
        """
        Initialize with a project repository.

        Args:
            repository: ProjectRepository instance for data access.
        """
        self._repository = repository

    async def get_project(self, project_id: UUID) -> ProjectResponse:
        """
        Retrieve a single project by ID.

        Args:
            project_id: UUID of the requested project.

        Returns:
            ProjectResponse with project data.

        Raises:
            ProjectNotFoundError: If no project exists with the given ID.
        """
        project: Project | None = await self._repository.get_project(project_id)

        if project is None:
            logger.info(
                "project_not_found",
                project_id=str(project_id),
            )
            raise ProjectNotFoundError(project_id=str(project_id))

        logger.debug(
            "project_retrieved",
            project_id=str(project_id),
            project_name=project.name,
        )

        return ProjectResponse.model_validate(project)
