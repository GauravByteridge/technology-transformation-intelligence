"""
DataSource service — business logic layer for data source and source connection operations.

Manages data source CRUD with credential isolation, and handles
project-to-data-source connection relationships (source connections).

Security Invariants:
- connection_config JSONB stores ONLY non-sensitive fields (host, port, database, schema)
- Credentials are stored separately in data_source_credentials as vault references
- API responses NEVER include raw credential values — only *_configured booleans
"""

import structlog
from uuid import UUID

from app.errors.datasource_errors import (
    DataSourceNotFoundError,
    DuplicateSourceConnectionError,
)
from app.errors.project_errors import ProjectNotFoundError
from app.models.data_source import DataSource, SourceConnection
from app.models.data_source_credential import DataSourceCredential
from app.repositories.credential_repository import CredentialRepository
from app.repositories.data_source_repository import DataSourceRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.security.credential_encryptor import CredentialEncryptor, SENSITIVE_FIELDS

logger = structlog.get_logger(__name__)


class DataSourceService:
    """
    Business logic for data source and source connection operations.

    Enforces credential isolation: connection_config stores ONLY non-sensitive
    parameters (host, port, database). Credentials are separated and stored
    in data_source_credentials as encrypted vault references. API responses
    never include credential values — only *_configured booleans.
    """

    def __init__(
        self,
        data_source_repository: DataSourceRepository,
        project_repository: ProjectRepository,
        source_connection_repository: SourceConnectionRepository,
        credential_encryptor: CredentialEncryptor,
        credential_repository: CredentialRepository | None = None,
    ) -> None:
        """
        Initialize with required dependencies.

        Args:
            data_source_repository: Repository for data source persistence.
            project_repository: Repository for project existence checks.
            source_connection_repository: Repository for source connection management.
            credential_encryptor: Encryptor for sensitive connection config fields.
            credential_repository: Repository for credential records (vault references).
        """
        self._data_source_repo = data_source_repository
        self._project_repo = project_repository
        self._source_connection_repo = source_connection_repository
        self._encryptor = credential_encryptor
        self._credential_repo = credential_repository

    async def create_data_source(
        self,
        name: str,
        source_type: str,
        display_label: str,
        connection_config: dict,
    ) -> dict:
        """
        Create a new data source with credential isolation.

        Separates sensitive fields (password, token, etc.) from connection_config
        before persistence. Non-sensitive fields are stored in connection_config JSONB.
        Credentials are encrypted and stored in data_source_credentials as vault references.

        Args:
            name: Data source display name.
            source_type: Type identifier (e.g., "postgresql", "mongodb").
            display_label: Human-friendly label for UI display.
            connection_config: Raw connection config (may include sensitive fields).

        Returns:
            Dictionary with data source fields and masked connection config.
        """
        # Separate credentials from non-sensitive connection parameters
        clean_config, credential_fields = self._separate_credentials(connection_config)

        data_source = DataSource(
            name=name,
            source_type=source_type,
            display_label=display_label,
            connection_config=clean_config,
        )

        created = await self._data_source_repo.create_data_source(data_source)

        # Store credentials as encrypted vault references in data_source_credentials
        if credential_fields and self._credential_repo:
            await self._store_credentials(created.id, credential_fields)

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

        If connection_config is in updates, credentials are separated from
        non-sensitive config. The clean config replaces existing connection_config.
        Credentials are re-encrypted and stored in data_source_credentials.

        Args:
            data_source_id: UUID of the data source to update.
            updates: Dictionary of field names to new values.

        Returns:
            Dictionary with updated data source fields and masked connection config.

        Raises:
            DataSourceNotFoundError: If no data source exists with the given ID.
        """
        if "connection_config" in updates:
            clean_config, credential_fields = self._separate_credentials(
                updates["connection_config"]
            )
            updates["connection_config"] = clean_config

            # Replace credentials in data_source_credentials table
            if self._credential_repo:
                await self._credential_repo.delete_by_data_source(data_source_id)
                if credential_fields:
                    await self._store_credentials(data_source_id, credential_fields)

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

    async def list_finance_sources_for_project(
        self, project_id: UUID
    ) -> list[dict]:
        """
        List data sources connected to a project for finance queries.

        Used by AI tools to discover available finance data sources.

        Args:
            project_id: UUID of the project to query.

        Returns:
            List of dicts describing connected data sources.
        """
        data_sources = await self._data_source_repo.list_by_project(project_id)

        logger.debug(
            "finance_sources_retrieved",
            project_id=str(project_id),
            source_count=len(data_sources),
        )

        return [
            {
                "id": str(source.id),
                "name": source.name,
                "source_type": source.source_type,
                "display_label": getattr(source, 'display_label', source.name),
                "connection_status": getattr(source, 'connection_status', source.status),
            }
            for source in data_sources
        ]

    def _to_response(self, data_source: DataSource) -> dict:
        """Convert a DataSource model to a response dict with credential indicators.

        connection_config now contains ONLY non-sensitive fields (host, port, database).
        Credential presence is indicated by checking data_source_credentials records.
        """
        config = data_source.connection_config or {}
        # Add credential configured indicators based on credentials relationship
        has_credentials = bool(data_source.credentials) if hasattr(data_source, 'credentials') else False
        response_config = dict(config)
        response_config["password_configured"] = has_credentials

        return {
            "id": data_source.id,
            "name": data_source.name,
            "source_type": data_source.source_type,
            "display_label": getattr(data_source, 'display_label', data_source.name),
            "connection_config": response_config,
            "connection_status": getattr(data_source, 'connection_status', data_source.status),
            "last_connected_at": getattr(data_source, 'last_connected_at', None),
            "created_at": data_source.created_at,
            "updated_at": data_source.updated_at,
            # Discovery tracking fields (Phase 8)
            "last_discovery_at": getattr(data_source, 'last_discovery_at', data_source.last_discovered_at),
            "discovery_status": data_source.discovery_status or "pending",
            "objects_discovered": getattr(data_source, 'objects_discovered', 0),
            "fields_discovered": getattr(data_source, 'fields_discovered', 0),
        }

    def _separate_credentials(self, config: dict) -> tuple[dict, dict]:
        """Separate credential fields from non-sensitive connection parameters.

        Returns:
            Tuple of (clean_config without credentials, credential_fields only).
        """
        clean_config: dict = {}
        credential_fields: dict = {}

        for key, value in config.items():
            if key in SENSITIVE_FIELDS:
                if value is not None and value != "":
                    credential_fields[key] = value
            else:
                clean_config[key] = value

        return clean_config, credential_fields

    async def _store_credentials(self, data_source_id: UUID, credential_fields: dict) -> None:
        """Store credentials as encrypted vault references in data_source_credentials.

        Each sensitive field is encrypted and stored as a separate credential record
        with credential_type indicating the field name and secret_reference containing
        the Fernet-encrypted value prefixed with 'vault://fernet/'.

        Args:
            data_source_id: UUID of the data source.
            credential_fields: Dictionary of sensitive field names to raw values.
        """
        if not self._credential_repo:
            return

        for field_name, raw_value in credential_fields.items():
            # Encrypt the raw value using Fernet
            encrypted_value = self._encryptor.encrypt_config({field_name: raw_value})[field_name]
            # Store as vault reference pattern
            vault_reference = f"vault://fernet/{encrypted_value}"

            credential = DataSourceCredential(
                data_source_id=data_source_id,
                credential_type=field_name,
                secret_reference=vault_reference,
            )
            await self._credential_repo.create_credential(credential)

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
