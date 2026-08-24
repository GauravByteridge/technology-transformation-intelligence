"""ConnectorService — orchestrates connector operations with security, timeout, and row-cap guarantees.

Design Decision (from Task 2.1):
    Credentials are stored separately in data_source_credentials as vault references.
    ConnectorService retrieves them, decrypts, and merges with connection_config
    at the connector execution boundary. Decrypted credentials exist ONLY within
    the _resolve_connector() scope — they are never persisted to connection_config.
"""

import asyncio
import time
from dataclasses import replace
from typing import Any
from uuid import UUID

import structlog

from app.connectors.protocol import DataSourceConnector, QueryResult, SourceMetadata, SourceQuery, SchemaInfo
from app.connectors.registry import ConnectorRegistry
from app.errors.datasource_errors import (
    DataSourceNotFoundError,
    QueryValidationError,
    TimeoutOperationError,
)
from app.repositories.credential_repository import CredentialRepository
from app.repositories.data_source_repository import DataSourceRepository
from app.security.credential_encryptor import CredentialEncryptor

logger = structlog.get_logger(__name__)

API_ROW_CAP: int = 10_000
API_OPERATION_TIMEOUT: int = 30  # seconds


class ConnectorService:
    """Orchestrates connector operations. Owns the 30-second API timeout budget."""

    def __init__(
        self,
        data_source_repository: DataSourceRepository,
        credential_encryptor: CredentialEncryptor,
        connector_registry: ConnectorRegistry,
        credential_repository: CredentialRepository | None = None,
    ) -> None:
        self._repo = data_source_repository
        self._encryptor = credential_encryptor
        self._registry = connector_registry
        self._credential_repo = credential_repository

    async def _resolve_connector(self, data_source_id: UUID) -> tuple[DataSourceConnector, str]:
        """Look up data source, retrieve and decrypt credentials, resolve connector.

        Credentials are retrieved from data_source_credentials table (vault references),
        decrypted, and merged with the non-sensitive connection_config. The merged config
        is passed to the connector. Decrypted credentials exist only within this scope.

        Falls back to decrypting connection_config directly if credential_repository is
        not available (backward compatibility during migration).

        Returns (connector_instance, source_type).

        Raises:
            DataSourceNotFoundError: If no data source with the given ID exists.
            UnsupportedDataSourceError: If the source type has no registered connector.
            CredentialDecryptionError: If credential decryption fails.
        """
        data_source = await self._repo.get_data_source(data_source_id)
        if data_source is None:
            raise DataSourceNotFoundError(data_source_id=str(data_source_id))

        # Start with the non-sensitive connection_config
        merged_config = dict(data_source.connection_config or {})

        # Retrieve credentials from data_source_credentials and merge
        if self._credential_repo:
            credentials = await self._credential_repo.get_by_data_source(data_source_id)
            for cred in credentials:
                # Extract encrypted value from vault reference
                vault_ref = cred.secret_reference
                if vault_ref.startswith("vault://fernet/"):
                    encrypted_value = vault_ref[len("vault://fernet/"):]
                    # Decrypt the single credential field
                    decrypted = self._encryptor.decrypt_config(
                        {cred.credential_type: encrypted_value}
                    )
                    merged_config.update(decrypted)
                else:
                    # NOTE: Unrecognized vault reference pattern — skip with warning
                    logger.warning(
                        "unrecognized_vault_reference",
                        data_source_id=str(data_source_id),
                        credential_type=cred.credential_type,
                    )
        else:
            # Backward compatibility: decrypt connection_config directly
            merged_config = self._encryptor.decrypt_config(merged_config)

        connector = self._registry.resolve(
            source_type=data_source.source_type,
            connection_config=merged_config,
        )
        return connector, data_source.source_type

    async def _execute_with_timeout(
        self, coro: Any, operation_name: str, deadline: float, source_id: str
    ) -> Any:
        """Wrap coroutine with remaining deadline budget.

        Computes remaining time from the shared 30s deadline and enforces it
        via asyncio.wait_for. ConnectorService is the SINGLE owner of the
        timeout budget — connectors receive no independent 30s timer.

        Raises:
            TimeoutOperationError: If the remaining budget is exhausted or the
                operation exceeds its allotted time.
        """
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            logger.warning(
                "connector_timeout",
                source_id=source_id,
                operation=operation_name,
                timeout_seconds=API_OPERATION_TIMEOUT,
            )
            raise TimeoutOperationError(
                operation=operation_name, timeout_seconds=API_OPERATION_TIMEOUT
            )
        try:
            return await asyncio.wait_for(coro, timeout=remaining)
        except asyncio.TimeoutError:
            logger.warning(
                "connector_timeout",
                source_id=source_id,
                operation=operation_name,
                timeout_seconds=API_OPERATION_TIMEOUT,
            )
            raise TimeoutOperationError(
                operation=operation_name, timeout_seconds=API_OPERATION_TIMEOUT
            )

    def _apply_row_cap(self, result: QueryResult) -> tuple[QueryResult, bool]:
        """Apply API_ROW_CAP and compute the truncated flag.

        Returns:
            Tuple of (possibly-capped QueryResult, truncated boolean).
            Truncated is True when the original result already indicated
            has_more_rows OR when row_count exceeds API_ROW_CAP.
        """
        truncated = result.has_more_rows or result.row_count > API_ROW_CAP

        if result.row_count > API_ROW_CAP:
            capped = replace(
                result,
                rows=result.rows[:API_ROW_CAP],
                row_count=API_ROW_CAP,
                has_more_rows=True,
            )
            return capped, True

        return result, truncated

    async def discover_metadata(self, data_source_id: UUID) -> SourceMetadata:
        """Discover metadata for a data source.

        Owns the 30s timeout budget. Resolves the connector, then executes
        discover_metadata() within the remaining budget.

        Returns:
            SourceMetadata from the connector.

        Raises:
            DataSourceNotFoundError: Data source not in DB.
            UnsupportedDataSourceError: Source type not registered.
            DataSourceConnectionError: External DB unreachable.
            SchemaDiscoveryError: Discovery operation failed.
            TimeoutOperationError: 30s budget exceeded.
        """
        source_id_str = str(data_source_id)
        logger.info(
            "connector_operation_started",
            source_id=source_id_str,
            operation="discover_metadata",
        )
        start = time.monotonic()
        deadline = start + API_OPERATION_TIMEOUT
        connector, source_type = await self._resolve_connector(data_source_id)
        result = await self._execute_with_timeout(
            connector.discover_metadata(),
            operation_name="discover_metadata",
            deadline=deadline,
            source_id=source_id_str,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "connector_operation_completed",
            source_id=source_id_str,
            operation="discover_metadata",
            duration_ms=round(elapsed_ms, 2),
        )
        return result

    async def discover_schema(self, data_source_id: UUID) -> SchemaInfo:
        """Discover schema for a data source.

        Owns the 30s timeout budget. Resolves the connector, then executes
        discover_schema() within the remaining budget.
        """
        source_id_str = str(data_source_id)
        logger.info(
            "connector_operation_started",
            source_id=source_id_str,
            operation="discover_schema",
        )
        start = time.monotonic()
        deadline = start + API_OPERATION_TIMEOUT
        connector, source_type = await self._resolve_connector(data_source_id)
        result = await self._execute_with_timeout(
            connector.discover_schema(),
            operation_name="discover_schema",
            deadline=deadline,
            source_id=source_id_str,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "connector_operation_completed",
            source_id=source_id_str,
            operation="discover_schema",
            duration_ms=round(elapsed_ms, 2),
        )
        return result

    async def execute_query(self, data_source_id: UUID, query: SourceQuery) -> tuple[QueryResult, bool]:
        """Execute a read-only query against a data source.

        Owns the 30s timeout budget. Resolves the connector, validates the query
        type matches the source (str for postgresql, dict for mongodb), executes
        within remaining budget, and applies API row cap.

        Returns:
            Tuple of (QueryResult capped at API_ROW_CAP, truncated: bool).

        Raises:
            DataSourceNotFoundError: Data source not in DB.
            UnsupportedDataSourceError: Source type not registered.
            QueryValidationError: Wrong query type for source (str for mongo, dict for pg).
            QueryExecutionError: External DB query failure.
            DataSourceConnectionError: External DB unreachable.
            TimeoutOperationError: 30s budget exceeded.
        """
        source_id_str = str(data_source_id)
        logger.info(
            "connector_operation_started",
            source_id=source_id_str,
            operation="execute_query",
        )
        start = time.monotonic()
        deadline = start + API_OPERATION_TIMEOUT
        connector, source_type = await self._resolve_connector(data_source_id)

        # Source-specific query type validation
        if source_type == "postgresql" and not isinstance(query, str):
            raise QueryValidationError(
                source_type=source_type,
                message="PostgreSQL queries must be SQL strings",
            )
        if source_type == "mongodb" and not isinstance(query, dict):
            raise QueryValidationError(
                source_type=source_type,
                message="MongoDB queries must be dictionaries",
            )

        result = await self._execute_with_timeout(
            connector.execute_read(query),
            operation_name="execute_query",
            deadline=deadline,
            source_id=source_id_str,
        )

        capped_result, truncated = self._apply_row_cap(result)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "connector_operation_completed",
            source_id=source_id_str,
            operation="execute_query",
            duration_ms=round(elapsed_ms, 2),
            row_count=capped_result.row_count,
        )
        return capped_result, truncated
