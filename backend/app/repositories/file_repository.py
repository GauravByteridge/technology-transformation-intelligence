"""
File repository — database access layer for uploaded file entities.

Provides typed, parameterized access to the uploaded_files table in App_DB.
All queries use SQLAlchemy ORM with bound parameters (inherited from BaseRepository).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.uploaded_file import UploadedFile
from app.repositories.base import BaseRepository


class FileRepository(BaseRepository[UploadedFile]):
    """
    Encapsulates all database access for UploadedFile entities.

    Inherits parameterized query patterns from BaseRepository.
    Services call this repository — it contains no business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession injected by the dependency container.
        """
        super().__init__(session, UploadedFile)

    async def get_file(self, file_id: UUID) -> UploadedFile | None:
        """
        Retrieve a file record by its primary key.

        Args:
            file_id: UUID of the uploaded file.

        Returns:
            UploadedFile model instance, or None if not found.
        """
        return await self._get_by_id(file_id)

    async def list_by_project(self, project_id: UUID) -> list[UploadedFile]:
        """
        Retrieve all uploaded files for a given project.

        Args:
            project_id: UUID of the project to filter by.

        Returns:
            List of UploadedFile instances for the project.
        """
        statement = select(UploadedFile).where(
            UploadedFile.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create_file(self, entity: UploadedFile) -> UploadedFile:
        """
        Persist a new uploaded file record to the database.

        Args:
            entity: UploadedFile model instance to persist.

        Returns:
            The persisted UploadedFile with server-generated fields populated.
        """
        return await self._create(entity)

    async def update_file(
        self, file_id: UUID, updates: dict
    ) -> UploadedFile | None:
        """
        Apply partial updates to an existing file record.

        Args:
            file_id: UUID of the file to update.
            updates: Dictionary of field names to new values.

        Returns:
            Updated UploadedFile instance, or None if not found.
        """
        uploaded_file = await self._get_by_id(file_id)
        if uploaded_file is None:
            return None

        for field, value in updates.items():
            if hasattr(uploaded_file, field):
                setattr(uploaded_file, field, value)

        await self._session.flush()
        await self._session.refresh(uploaded_file)
        return uploaded_file

    async def delete_file(self, file_id: UUID) -> bool:
        """
        Delete a file record by its primary key.

        Args:
            file_id: UUID of the file to delete.

        Returns:
            True if the file was deleted, False if not found.
        """
        return await self._delete_by_id(file_id)
