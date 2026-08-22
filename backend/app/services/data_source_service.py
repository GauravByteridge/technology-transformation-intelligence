"""
DataSource service — business logic layer for data source and source connection operations.

Manages data source CRUD with credential encryption/masking, and handles
project-to-data-source connection relationships (source connections).
"""

import structlog
from uuid import UUID

from app.errors.datasource_errors import (
    DataSourceNotFoundError,
    DuplicateSourceConnectionError,
)
from app.errors.project_errors import ProjectNotFoundError
from app.models.data_source import DataSource, SourceConnection
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.security.credential_encryptor import CredentialEncryptor

logger = structlog.get_logger(__name__)


class DataSourceService:
    """
    Business logic for data source and source connection operations.

    Enforces credential masking on all responses — plaintext secrets never
    leave the service boundary. Connection configs are encrypted before
    persistence and masked (never decrypted) for API responses.
    """

    def __init__(
        self,
        data_source_repository: DataSourceRepository,
        project_repository: ProjectRepository,
        source_connection_repository: SourceConnectionRepository,
        credential_encryptor: CredentialEncryptor,
    ) -> None:
        """
        Initialize with required dependencies.

        Args:
            data_source_repository: Repository for data source persistence.
            project_repository: Repository for project existence checks.
            source_connection_repository: Repository for source connection management.
            credential_encryptor: Encryptor for sensitive connection config fields.
        """
        self._data_source_repo = data_source_repository
        self._project_repo = project_repository
        self._source_connection_repo = source_connection_repository
        self._encryptor = credential_encryptor

    async def create_data_source(
        self,
        name: str,
        source_type: str,
        display_label: str,
        connection_config: dict,
    ) -> dict:
        """
        Create a new data source with encrypted connection config.

        Args:
            name: Data source display name.
            source_type: Type identifier (e.g., "postgresql", "mongodb").
            display_label: Human-friendly label for UI display.
            connection_config: Raw connection config (sensitive fields will be encrypted).

        Returns:
            Dictionary with data source fields and masked connection config.
        """
        encrypted_config = self._encryptor.encrypt_config(connection_config)

        data_source = DataSource(
            name=name,
            source_type=source_type,
            display_label=display_label,
            connection_config=encrypted_config,
        )

        created = await self._data_source_repo.create_data_source(data_source)

        logger.info(
            "data_source_created",
            data_source_id=str(created.id),
            source_type=source_type,
        )

        return self._to_response(created)

    async def get_data_source(self, data_source_id: UUID) -> dict:
        """
        Retrieve a data source by ID with masked config.

        Args:
            data_source_id: UUID of the data source.

        Returns:
            Dictionary with data source fields and masked connection config.

        Raises:
            DataSourceNotFoundError: If no data source exists with the given ID.
        """
        data_source = await self._data_source_repo.get_data_source(data_source_id)

        if data_source is None:
            logger.info("data_source_not_found", data_source_id=str(data_source_id))
            raise DataSourceNotFoundError(data_source_id=str(data_source_id))

        return self._to_response(data_source)

    async def list_data_sources(self) -> list[dict]:
        """
        List all data sources with masked configs.

        Returns:
            List of dictionaries with data source fields and masked connection configs.
        """
        data_sources = await self._data_source_repo.list_data_sources()

        logger.debug("data_sources_listed", total=len(data_sources))

        return [self._to_response(ds) for ds in data_sources]

    async def update_data_source(
        self,
        data_source_id: UUID,
        updates: dict,
    ) -> dict:
        """
        Update a data source. connection_config is a COMPLETE REPLACEMENT.

        If connection_config is in updates, the entire new config is encrypted
        before persistence (not merged with existing).

        Args:
            data_source_id: UUID of the data source to update.
            updates: Dictionary of field names to new values.

        Returns:
            Dictionary with updated data source fields and masked connection config.

        Raises:
            DataSourceNotFoundError: If no data source exists with the given ID.
        """
        if "connection_config" in updates:
            updates["connection_config"] = self._encryptor.encrypt_config(
                updates["connection_config"]
            )

        updated = await self._data_source_repo.update_data_source(data_source_id, updates)

        if updated is None:
            logger.info(
                "data_source_not_found_for_update",
                data_source_id=str(data_source_id),
            )
            raise DataSourceNotFoundError(data_source_id=str(data_source_id))

        logger.info(
            "data_source_updated",
            data_source_id=str(data_source_id),
            updated_fields=list(updates.keys()),
        )

        return self._to_response(updated)

    async def delete_data_source(self, data_source_id: UUID) -> None:
        """
        Delete a data source. FK cascade handles source_connections removal.

        Args:
            data_source_id: UUID of the data source to delete.

        Raises:
            DataSourceNotFoundError: If no data source exists with the given ID.
        """
        deleted = await self._data_source_repo.delete_data_source(data_source_id)

        if not deleted:
            logger.info(
                "data_source_not_found_for_delete",
                data_source_id=str(data_source_id),
            )
            raise DataSourceNotFoundError(data_source_id=str(data_source_id))

        logger.info("data_source_deleted", data_source_id=str(data_source_id))

    # --- Source Connection Operations ---

    async def create_source_connection(
        self,
        project_id: UUID,
        data_source_id: UUID,
        purpose: str,
    ) -> dict:
        """
        Create a connection between a project and a data source.

        Verifies both project and data source exist before creating.

        Args:
            project_id: UUID of the project.
            data_source_id: UUID of the data source.
            purpose: Description of why this source is connected.

        Returns:
            Dictionary with source connection fields.

        Raises:
            ProjectNotFoundError: If the project does not exist.
            DataSourceNotFoundError: If the data source does not exist.
            DuplicateSourceConnectionError: If the connection already exists.
        """
        project = await self._project_repo.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id=str(project_id))

        data_source = await self._data_source_repo.get_data_source(data_source_id)
        if data_source is None:
            raise DataSourceNotFoundError(data_source_id=str(data_source_id))

        connection = SourceConnection(
            project_id=project_id,
            data_source_id=data_source_id,
            purpose=purpose,
        )

        created = await self._source_connection_repo.create_connection(connection)

        logger.info(
            "source_connection_created",
            project_id=str(project_id),
            data_source_id=str(data_source_id),
        )

        return self._connection_to_response(created)

    async def list_source_connections(self, project_id: UUID) -> list[dict]:
        """
        List all source connections for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of dictionaries with source connection fields.
        """
        connections = await self._source_connection_repo.list_by_project(project_id)

        return [self._connection_to_response(c) for c in connections]

    async def delete_source_connection(
        self,
        project_id: UUID,
        data_source_id: UUID,
    ) -> None:
        """
        Delete a source connection between a project and data source.

        Args:
            project_id: UUID of the project.
            data_source_id: UUID of the data source.

        Raises:
            DataSourceNotFoundError: If the connection does not exist.
        """
        deleted = await self._source_connection_repo.delete_connection(
            project_id, data_source_id
        )

        if not deleted:
            raise DataSourceNotFoundError(data_source_id=str(data_source_id))

        logger.info(
            "source_connection_deleted",
            project_id=str(project_id),
            data_source_id=str(data_source_id),
        )

    # --- Private Helpers ---

    def _to_response(self, data_source: DataSource) -> dict:
        """Convert a DataSource model to a response dict with masked config."""
        return {
            "id": data_source.id,
            "name": data_source.name,
            "source_type": data_source.source_type,
            "display_label": data_source.display_label,
            "connection_config": self._encryptor.mask_config(
                data_source.connection_config or {}
            ),
            "connection_status": data_source.connection_status,
            "last_connected_at": data_source.last_connected_at,
            "created_at": data_source.created_at,
            "updated_at": data_source.updated_at,
        }

    def _connection_to_response(self, connection: SourceConnection) -> dict:
        """Convert a SourceConnection model to a response dict."""
        return {
            "id": connection.id,
            "project_id": connection.project_id,
            "data_source_id": connection.data_source_id,
            "purpose": connection.purpose,
            "created_at": connection.created_at,
            "updated_at": connection.updated_at,
        }
