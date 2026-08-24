"""
ProjectSourceMapping repository — database access layer for project-source mapping entities.

Provides typed, parameterized access to the project_source_mappings table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).

Project source mappings link projects to catalog entries via data sources,
enabling project-scoped queries to access only relevant data without duplicating
schema discovery per project.
"""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_source_mapping import ProjectSourceMapping
from app.repositories.base import BaseRepository


class ProjectSourceMappingRepository(BaseRepository[ProjectSourceMapping]):
    """
    Encapsulates all database access for ProjectSourceMapping entities.

    Inherits parameterized query patterns from BaseRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, ProjectSourceMapping)

    async def create_mapping(
        self, mapping: ProjectSourceMapping
    ) -> ProjectSourceMapping:
        """
        Persist a new project-source mapping to the database.

        Args:
            mapping: ProjectSourceMapping model instance to persist.

        Returns:
            The persisted mapping with server-generated fields populated.
        """
        return await self._create(mapping)

    async def get_mappings_by_project(
        self, project_id: UUID
    ) -> list[ProjectSourceMapping]:
        """
        Retrieve all source mappings for a specific project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of ProjectSourceMapping instances for the given project.
        """
        statement = select(ProjectSourceMapping).where(
            ProjectSourceMapping.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_mappings_by_source(
        self, source_id: UUID
    ) -> list[ProjectSourceMapping]:
        """
        Retrieve all project mappings that reference a specific data source.

        Args:
            source_id: UUID of the data source to filter by.

        Returns:
            List of ProjectSourceMapping instances for the given source.
        """
        statement = select(ProjectSourceMapping).where(
            ProjectSourceMapping.source_id == source_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def delete_mappings_for_project(self, project_id: UUID) -> int:
        """
        Delete all source mappings for a given project.

        Used when re-running discovery or clearing project associations.

        Args:
            project_id: UUID of the project whose mappings to delete.

        Returns:
            Count of deleted mappings.
        """
        statement = delete(ProjectSourceMapping).where(
            ProjectSourceMapping.project_id == project_id
        )
        result = await self._session.execute(statement)
        return result.rowcount  # type: ignore[return-value]

    async def upsert_mapping(
        self,
        project_id: UUID,
        catalog_entry_id: UUID,
        source_id: UUID,
        project_field: str,
        mapping_type: str = "discovered",
    ) -> ProjectSourceMapping:
        """
        Insert or update an existing project-source mapping.

        Uses the unique constraint on (project_id, catalog_entry_id) to detect
        existing mappings. If found, updates source_id, project_field, and
        mapping_type. Otherwise, creates a new mapping.

        Args:
            project_id: UUID of the project.
            catalog_entry_id: UUID of the catalog entry being mapped.
            source_id: UUID of the data source.
            project_field: Field name used for project filtering.
            mapping_type: Type of mapping — "discovered" or "configured".

        Returns:
            The created or updated ProjectSourceMapping instance.
        """
        # Check for existing mapping by unique constraint fields
        statement = select(ProjectSourceMapping).where(
            ProjectSourceMapping.project_id == project_id,
            ProjectSourceMapping.catalog_entry_id == catalog_entry_id,
        )
        result = await self._session.execute(statement)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.source_id = source_id
            existing.project_field = project_field
            existing.mapping_type = mapping_type
            await self._session.flush()
            await self._session.refresh(existing)
            return existing

        # Create new mapping
        new_mapping = ProjectSourceMapping(
            project_id=project_id,
            catalog_entry_id=catalog_entry_id,
            source_id=source_id,
            project_field=project_field,
            mapping_type=mapping_type,
        )
        return await self._create(new_mapping)
