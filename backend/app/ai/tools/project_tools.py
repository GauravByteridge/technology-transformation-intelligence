"""
Project domain AI tools.

Provides the AI agent with project context retrieval capabilities.
Tools call domain services only — never repositories or connectors directly.

WARNING: Do NOT add hardcoded project names, descriptions, or demo data.
Demo Mode uses seeded data retrieved through service → repository → database.
"""

import structlog
from typing import Any
from uuid import UUID

from app.errors.project_errors import ProjectNotFoundError
from app.services.project_service import ProjectService

logger = structlog.get_logger(__name__)


def create_get_project_context(project_service: ProjectService):
    """
    Factory that creates the get_project_context tool function.

    Uses closure to inject the ProjectService dependency, keeping
    the tool function signature clean for the agent invocation.

    Args:
        project_service: Injected ProjectService for data access.

    Returns:
        Async tool function accepting project_id and returning project context dict.
    """

    async def get_project_context(project_id: UUID) -> dict[str, Any]:
        """
        Retrieve project context for AI agent consumption.

        Fetches project data through ProjectService → ProjectRepository → App_DB.
        Returns a structured dict the agent uses to ground its responses.

        Args:
            project_id: UUID of the project to retrieve context for.

        Returns:
            Dict containing project info and source attribution label.

        Raises:
            ProjectNotFoundError: If the project does not exist.
        """
        logger.info(
            "tool_get_project_context_invoked",
            extra={"project_id": str(project_id)},
        )

        project = await project_service.get_project(project_id)

        return {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "status": project.status,
                "description": project.description,
            },
            "source_label": "App_DB → projects",
        }

    return get_project_context
