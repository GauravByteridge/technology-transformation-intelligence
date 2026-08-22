"""
Project service — business logic layer for project operations.

Accepts ProjectRepository via constructor injection. Contains business
logic and delegates data access to the repository layer.
"""

import structlog
from uuid import UUID

from app.constants import SYSTEM_USER_ID
from app.errors.project_errors import ProjectNotFoundError
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.projects import ProjectCreate, ProjectListResponse, ProjectResponse

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

    async def create_project(self, data: ProjectCreate) -> ProjectResponse:
        """
        Create a new project with active status.

        Uses SYSTEM_USER_ID as created_by until authentication is implemented.

        Args:
            data: Validated project creation payload.

        Returns:
            ProjectResponse with the newly created project data.
        """
        project = Project(
            name=data.name,
            description=data.description,
            status="active",
            created_by=SYSTEM_USER_ID,
        )

        created = await self._repository.create_project(project)

        logger.info(
            "project_created",
            project_id=str(created.id),
            project_name=created.name,
        )

        return ProjectResponse.model_validate(created)

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

    async def list_projects(self) -> ProjectListResponse:
        """
        List all projects.

        Returns:
            ProjectListResponse with items and total count.
        """
        projects = await self._repository.list_projects()

        logger.debug("projects_listed", total=len(projects))

        items = [ProjectResponse.model_validate(p) for p in projects]
        return ProjectListResponse(items=items, total=len(items))

    async def update_project(self, project_id: UUID, updates: dict) -> ProjectResponse:
        """
        Apply partial updates to an existing project.

        Args:
            project_id: UUID of the project to update.
            updates: Dictionary of field names to new values.

        Returns:
            ProjectResponse with updated project data.

        Raises:
            ProjectNotFoundError: If no project exists with the given ID.
        """
        updated = await self._repository.update_project(project_id, updates)

        if updated is None:
            logger.info(
                "project_not_found_for_update",
                project_id=str(project_id),
            )
            raise ProjectNotFoundError(project_id=str(project_id))

        logger.info(
            "project_updated",
            project_id=str(project_id),
            updated_fields=list(updates.keys()),
        )

        return ProjectResponse.model_validate(updated)

    async def delete_project(self, project_id: UUID) -> None:
        """
        Delete a project by ID.

        Args:
            project_id: UUID of the project to delete.

        Raises:
            ProjectNotFoundError: If no project exists with the given ID.
        """
        deleted = await self._repository.delete_project(project_id)

        if not deleted:
            logger.info(
                "project_not_found_for_delete",
                project_id=str(project_id),
            )
            raise ProjectNotFoundError(project_id=str(project_id))

        logger.info(
            "project_deleted",
            project_id=str(project_id),
        )
