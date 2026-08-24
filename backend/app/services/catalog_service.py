"""
CatalogService — business logic for the Enterprise Data Catalog.

Coordinates catalog versioning, project mapping management, and search.
The catalog belongs to data sources, not projects — project mappings are
maintained as a separate relationship layer.
"""

import structlog
from uuid import UUID

from app.models.catalog_entry import CatalogEntry
from app.models.project_source_mapping import ProjectSourceMapping
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.project_source_mapping_repository import (
    ProjectSourceMappingRepository,
)

logger = structlog.get_logger(__name__)


class CatalogService:
    """
    Business logic for Enterprise Data Catalog operations.

    Responsibilities:
    - Versioned storage of discovery results
    - Project-to-catalog mapping management
    - Catalog search and retrieval

    The service enforces the principle that catalog entries belong to data
    sources. Projects access catalog data through explicit mappings.
    """

    def __init__(
        self,
        catalog_repository: CatalogRepository,
        project_source_mapping_repository: ProjectSourceMappingRepository,
    ) -> None:
        """
        Initialize with required repositories.

        Args:
            catalog_repository: Repository for catalog entry persistence.
            project_source_mapping_repository: Repository for project mapping management.
        """
        self._catalog_repo = catalog_repository
        self._mapping_repo = project_source_mapping_repository

    async def store_discovery_results(
        self, source_id: UUID, entries: list[CatalogEntry]
    ) -> int:
        """
        Store discovery results as new versioned catalog entries.

        For each entry, calculates the next version number for the
        source_id + object_name combination, ensuring previous versions
        are preserved for audit purposes.

        Args:
            source_id: UUID of the data source these entries belong to.
            entries: List of CatalogEntry instances to persist (version field
                     will be set by this method).

        Returns:
            The number of entries successfully stored.
        """
        stored_count = 0

        for entry in entries:
            current_version = await self._catalog_repo.get_latest_version(
                source_id, entry.object_name
            )
            next_version = current_version + 1
            entry.version = next_version
            entry.source_id = source_id

            await self._catalog_repo.create_entry(entry)
            stored_count += 1

        logger.info(
            "discovery_results_stored",
            source_id=str(source_id),
            entries_stored=stored_count,
        )

        return stored_count

    async def get_catalog_for_project(self, project_id: UUID) -> list[CatalogEntry]:
        """
        Retrieve catalog entries mapped to a project.

        Delegates to CatalogRepository which joins through project_source_mappings.

        Args:
            project_id: UUID of the project.

        Returns:
            List of CatalogEntry instances mapped to the project.
        """
        entries = await self._catalog_repo.get_entries_by_project(project_id)

        logger.debug(
            "catalog_retrieved_for_project",
            project_id=str(project_id),
            entry_count=len(entries),
        )

        return entries

    async def get_catalog_for_source(self, source_id: UUID) -> list[CatalogEntry]:
        """
        Retrieve catalog entries for a data source (latest versions only).

        Args:
            source_id: UUID of the data source.

        Returns:
            List of CatalogEntry instances for the source.
        """
        entries = await self._catalog_repo.get_entries_by_source(source_id)

        logger.debug(
            "catalog_retrieved_for_source",
            source_id=str(source_id),
            entry_count=len(entries),
        )

        return entries

    async def search_catalog(
        self, query: str, project_id: UUID | None = None
    ) -> list[CatalogEntry]:
        """
        Search catalog entries by natural-language query.

        Matches against object names, semantic names, and descriptions.
        Optionally scoped to entries mapped to a specific project.

        Args:
            query: Natural-language search string.
            project_id: Optional project UUID to scope results.

        Returns:
            List of matching CatalogEntry instances.
        """
        entries = await self._catalog_repo.search_entries(query, project_id)

        logger.debug(
            "catalog_search_executed",
            query=query,
            project_id=str(project_id) if project_id else None,
            results_count=len(entries),
        )

        return entries

    async def get_catalog_entry(self, entry_id: UUID) -> CatalogEntry | None:
        """
        Retrieve a single catalog entry by ID.

        Args:
            entry_id: UUID of the catalog entry.

        Returns:
            The CatalogEntry instance or None if not found.
        """
        return await self._catalog_repo.get_entry_by_id(entry_id)

    async def get_project_mappings(
        self, project_id: UUID
    ) -> list[ProjectSourceMapping]:
        """
        Retrieve all project-to-catalog mappings for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of ProjectSourceMapping instances for the project.
        """
        return await self._mapping_repo.get_mappings_by_project(project_id)

    async def update_project_mappings(
        self, project_id: UUID, mappings: list[ProjectSourceMapping]
    ) -> None:
        """
        Replace all project mappings for a project.

        Deletes existing mappings and creates new ones in a single operation.
        This is an atomic replacement — if the caller needs partial updates,
        they should use individual mapping operations directly.

        Args:
            project_id: UUID of the project whose mappings to replace.
            mappings: New list of ProjectSourceMapping instances to persist.
        """
        deleted_count = await self._mapping_repo.delete_mappings_for_project(project_id)

        for mapping in mappings:
            mapping.project_id = project_id
            await self._mapping_repo.create_mapping(mapping)

        logger.info(
            "project_mappings_updated",
            project_id=str(project_id),
            deleted_count=deleted_count,
            new_count=len(mappings),
        )
