"""
Project repository — database access layer for project entities.

Provides typed, parameterized access to the projects table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """
    Encapsulates all database access for Project entities.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, Project)

    async def get_project(self, project_id: UUID) -> Project | None:
        """
        Retrieve a project by its primary key.

        Args:
            project_id: UUID of the project to retrieve.

        Returns:
            Project model instance, or None if not found.
        """
        return await self._get_by_id(project_id)

    async def list_projects(self) -> list[Project]:
        """
        Retrieve all projects.

        Returns:
            List of all Project model instances.
        """
        return await self._list_all()

    async def create_project(self, project: Project) -> Project:
        """
        Persist a new project to the database.

        Args:
            project: Project model instance to persist.

        Returns:
            The persisted Project with server-generated fields populated.
        """
        return await self._create(project)
