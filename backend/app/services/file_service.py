"""
File service — business logic layer for uploaded file operations.

Manages file record CRUD with project and data source existence verification.
Actual file storage is handled externally; this service manages metadata records.
"""

import structlog
from uuid import UUID

from app.constants import SYSTEM_USER_ID
from app.errors.datasource_errors import DataSourceNotFoundError
from app.errors.file_errors import FileNotFoundError as DomainFileNotFoundError
from app.errors.project_errors import ProjectNotFoundError
from app.models.uploaded_file import UploadedFile
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import ProjectRepository

logger = structlog.get_logger(__name__)


class FileService:
    """
    Business logic for uploaded file metadata operations.

    Enforces project existence (and optional data source existence)
    before creating file records. Uses SYSTEM_USER_ID as uploaded_by.
    """

    def __init__(
        self,
        file_repository: FileRepository,
        project_repository: ProjectRepository,
        data_source_repository: DataSourceRepository,
    ) -> None:
        """
        Initialize with required dependencies.

        Args:
            file_repository: Repository for file record persistence.
            project_repository: Repository for project existence checks.
            data_source_repository: Repository for data source existence checks.
        """
        self._file_repo = file_repository
        self._project_repo = project_repository
        self._data_source_repo = data_source_repository

    async def create_file(
        self,
        project_id: UUID,
        file_name: str,
        file_type: str,
        file_size: int,
        data_source_id: UUID | None = None,
    ) -> dict:
        """
        Create a new file record.

        Verifies project exists. If data_source_id is provided, verifies
        the data source exists as well. Sets uploaded_by to SYSTEM_USER_ID.

        Args:
            project_id: UUID of the project this file belongs to.
            file_name: Original file name.
            file_type: File type/extension (e.g., "pdf", "csv").
            file_size: File size in bytes.
            data_source_id: Optional UUID of an associated data source.

        Returns:
            Dictionary with file record fields.

        Raises:
            ProjectNotFoundError: If the project does not exist.
            DataSourceNotFoundError: If data_source_id is provided and does not exist.
        """
        project = await self._project_repo.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id=str(project_id))

        if data_source_id is not None:
            data_source = await self._data_source_repo.get_data_source(data_source_id)
            if data_source is None:
                raise DataSourceNotFoundError(data_source_id=str(data_source_id))

        uploaded_file = UploadedFile(
            project_id=project_id,
            data_source_id=data_source_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            uploaded_by=SYSTEM_USER_ID,
        )

        created = await self._file_repo.create_file(uploaded_file)

        logger.info(
            "file_created",
            file_id=str(created.id),
            project_id=str(project_id),
            file_name=file_name,
        )

        return self._to_response(created)

    async def get_file(self, file_id: UUID) -> dict:
        """
        Retrieve a file record by ID.

        Args:
            file_id: UUID of the file record.

        Returns:
            Dictionary with file record fields.

        Raises:
            DomainFileNotFoundError: If the file does not exist.
        """
        uploaded_file = await self._file_repo.get_file(file_id)

        if uploaded_file is None:
            logger.info("file_not_found", file_id=str(file_id))
            raise DomainFileNotFoundError(file_id=str(file_id))

        return self._to_response(uploaded_file)

    async def list_by_project(self, project_id: UUID) -> list[dict]:
        """
        List all files for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of file record dictionaries.
        """
        files = await self._file_repo.list_by_project(project_id)

        logger.debug(
            "files_listed",
            project_id=str(project_id),
            total=len(files),
        )

        return [self._to_response(f) for f in files]

    async def update_file(self, file_id: UUID, updates: dict) -> dict:
        """
        Apply partial updates to a file record.

        Args:
            file_id: UUID of the file to update.
            updates: Dictionary of field names to new values.

        Returns:
            Dictionary with updated file record fields.

        Raises:
            DomainFileNotFoundError: If the file does not exist.
        """
        updated = await self._file_repo.update_file(file_id, updates)

        if updated is None:
            logger.info("file_not_found_for_update", file_id=str(file_id))
            raise DomainFileNotFoundError(file_id=str(file_id))

        logger.info(
            "file_updated",
            file_id=str(file_id),
            updated_fields=list(updates.keys()),
        )

        return self._to_response(updated)

    async def delete_file(self, file_id: UUID) -> None:
        """
        Delete a file record by ID.

        Args:
            file_id: UUID of the file to delete.

        Raises:
            DomainFileNotFoundError: If the file does not exist.
        """
        deleted = await self._file_repo.delete_file(file_id)

        if not deleted:
            logger.info("file_not_found_for_delete", file_id=str(file_id))
            raise DomainFileNotFoundError(file_id=str(file_id))

        logger.info("file_deleted", file_id=str(file_id))

    # --- Private Helpers ---

    def _to_response(self, uploaded_file: UploadedFile) -> dict:
        """Convert an UploadedFile model to a response dict."""
        return {
            "id": uploaded_file.id,
            "project_id": uploaded_file.project_id,
            "data_source_id": uploaded_file.data_source_id,
            "file_name": uploaded_file.file_name,
            "file_type": uploaded_file.file_type,
            "file_size": uploaded_file.file_size,
            "processing_status": uploaded_file.processing_status,
            "processing_error": uploaded_file.processing_error,
            "uploaded_by": uploaded_file.uploaded_by,
            "uploaded_at": uploaded_file.uploaded_at,
            "created_at": uploaded_file.created_at,
            "updated_at": uploaded_file.updated_at,
        }
