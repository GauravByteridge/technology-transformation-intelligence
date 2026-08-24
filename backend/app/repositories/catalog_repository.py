"""
CatalogRepository — database access for the Enterprise Data Catalog.

Provides typed, parameterized access to the catalog_entries table in App_DB.
Supports versioned catalog entries, source-scoped queries, project-scoped
queries (via join to project_source_mappings), and text-based search.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog_entry import CatalogEntry
from app.models.project_source_mapping import ProjectSourceMapping
from app.repositories.base import BaseRepository


class CatalogRepository(BaseRepository[CatalogEntry]):
    """
    Encapsulates all database access for CatalogEntry entities.

    Catalog entries represent discovered data objects (tables, collections,
    documents) enriched with semantic metadata for cross-source intelligence.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, CatalogEntry)

    async def create_entry(self, entry: CatalogEntry) -> CatalogEntry:
        """
        Persist a new catalog entry.

        Args:
            entry: CatalogEntry model instance to persist.

        Returns:
            The persisted CatalogEntry with server-generated fields populated.
        """
        return await self._create(entry)

    async def bulk_create_entries(self, entries: list[CatalogEntry]) -> list[CatalogEntry]:
        """
        Persist multiple catalog entries in a single flush.

        Args:
            entries: List of CatalogEntry model instances to persist.

        Returns:
            List of persisted entries with server-generated fields populated.
        """
        for entry in entries:
            self._session.add(entry)
        await self._session.flush()
        for entry in entries:
            await self._session.refresh(entry)
        return entries

    async def get_entry_by_id(self, entry_id: UUID) -> CatalogEntry | None:
        """
        Retrieve a single catalog entry by its primary key.

        Args:
            entry_id: UUID primary key of the catalog entry.

        Returns:
            The CatalogEntry instance or None if not found.
        """
        return await self._get_by_id(entry_id)

    async def get_entries_by_source(self, source_id: UUID) -> list[CatalogEntry]:
        """
        Retrieve all catalog entries for a given data source (latest versions only).

        Args:
            source_id: UUID of the data source.

        Returns:
            List of CatalogEntry instances belonging to the source.
        """
        # Subquery to get the max version for each object_name in this source
        max_version_subq = (
            select(
                CatalogEntry.object_name,
                func.max(CatalogEntry.version).label("max_version"),
            )
            .where(CatalogEntry.source_id == source_id)
            .group_by(CatalogEntry.object_name)
            .subquery()
        )

        statement = (
            select(CatalogEntry)
            .join(
                max_version_subq,
                (CatalogEntry.object_name == max_version_subq.c.object_name)
                & (CatalogEntry.version == max_version_subq.c.max_version),
            )
            .where(CatalogEntry.source_id == source_id)
        )

        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_entries_by_project(self, project_id: UUID) -> list[CatalogEntry]:
        """
        Retrieve catalog entries mapped to a project via project_source_mappings.

        Args:
            project_id: UUID of the project.

        Returns:
            List of CatalogEntry instances mapped to the project.
        """
        statement = (
            select(CatalogEntry)
            .join(
                ProjectSourceMapping,
                ProjectSourceMapping.catalog_entry_id == CatalogEntry.id,
            )
            .where(ProjectSourceMapping.project_id == project_id)
        )

        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def search_entries(
        self, query: str, project_id: UUID | None = None
    ) -> list[CatalogEntry]:
        """
        Search catalog entries by text relevance across semantic fields.

        Matches against object_name, semantic_name, and semantic_description
        using case-insensitive ILIKE patterns.

        Args:
            query: Natural-language search query.
            project_id: Optional project UUID to scope results.

        Returns:
            List of matching CatalogEntry instances ranked by relevance.
        """
        search_pattern = f"%{query}%"

        statement = select(CatalogEntry).where(
            (CatalogEntry.object_name.ilike(search_pattern))
            | (CatalogEntry.semantic_name.ilike(search_pattern))
            | (CatalogEntry.semantic_description.ilike(search_pattern))
        )

        if project_id is not None:
            statement = statement.join(
                ProjectSourceMapping,
                ProjectSourceMapping.catalog_entry_id == CatalogEntry.id,
            ).where(ProjectSourceMapping.project_id == project_id)

        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_version(self, source_id: UUID, object_name: str) -> int:
        """
        Get the latest version number for a specific source + object_name combination.

        Args:
            source_id: UUID of the data source.
            object_name: Name of the discovered object (table/collection).

        Returns:
            The highest version number, or 0 if no entries exist.
        """
        statement = select(func.max(CatalogEntry.version)).where(
            (CatalogEntry.source_id == source_id)
            & (CatalogEntry.object_name == object_name)
        )

        result = await self._session.execute(statement)
        max_version = result.scalar_one_or_none()
        return max_version or 0

    async def list_versions(
        self, source_id: UUID, object_name: str
    ) -> list[CatalogEntry]:
        """
        List all versions of a catalog entry for a given source + object_name.

        Args:
            source_id: UUID of the data source.
            object_name: Name of the discovered object.

        Returns:
            List of CatalogEntry instances ordered by version (ascending).
        """
        statement = (
            select(CatalogEntry)
            .where(
                (CatalogEntry.source_id == source_id)
                & (CatalogEntry.object_name == object_name)
            )
            .order_by(CatalogEntry.version.asc())
        )

        result = await self._session.execute(statement)
        return list(result.scalars().all())
