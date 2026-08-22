"""
PostgreSQL connector implementing the DataSourceConnector protocol.

Provides read-only access to PostgreSQL databases using asyncpg for
connection management and query execution.

Security Model — Read-Only Access Enforcement:
    1. Only `execute_read()` is exposed in the DataSourceConnector interface.
       There are no write methods (INSERT, UPDATE, DELETE) available.
    2. External database credentials MUST be configured with SELECT-only
       permissions (e.g., a PostgreSQL role granted only SELECT privileges).
    3. The platform does NOT parse or validate SQL for safety — database-level
       permissions are the sole enforcement mechanism.

WARNING: Do not configure this connector with credentials that have write access.
         Always use a dedicated read-only PostgreSQL role.

NOTE: Full query execution is deferred to Phase 1. Currently only
      `test_connection()` performs a real operation; other methods raise
      NotImplementedError.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg

from app.connectors.protocol import (
    QueryResult,
    SchemaInfo,
    SourceMetadata,
    SourceQuery,
)
from app.errors.datasource_errors import (
    DataSourceConnectionError,
    QueryExecutionError,
    SchemaDiscoveryError,
)

logger = logging.getLogger(__name__)

# Connection config keys
_REQUIRED_CONFIG_KEYS = ("host", "port", "database", "user", "password")


class PostgresConnector:
    """PostgreSQL connector with read-only access via asyncpg.

    Implements the DataSourceConnector protocol. Accepts parameterized
    SQL strings as the native query format.

    Args:
        connection_config: Dict with keys: host, port, database, user, password.

    Security:
        Read-only access is enforced by:
        - Only exposing `execute_read()` (no write operations in the interface)
        - Requiring that database credentials have SELECT-only grants
        - The platform does NOT implement a SQL parser or query security engine;
          database-level permissions are the enforcement mechanism
    """

    SOURCE_TYPE = "postgresql"

    def __init__(self, connection_config: dict[str, Any]) -> None:
        self._config = connection_config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate that required connection configuration keys are present."""
        missing = [key for key in _REQUIRED_CONFIG_KEYS if key not in self._config]
        if missing:
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Missing required connection config keys: {', '.join(missing)}",
                detail=f"source_id={self._config.get('source_id', 'unknown')}, "
                f"operation=validate_config",
            )

    async def test_connection(self, timeout: int = 10) -> bool:
        """Attempt a real connection to the PostgreSQL database.

        Uses asyncpg to connect with the configured credentials and timeout.
        Returns True on success, raises DataSourceConnectionError on failure.

        Args:
            timeout: Maximum seconds to wait for connection (default: 10).

        Returns:
            True if the connection succeeds.

        Raises:
            DataSourceConnectionError: If the connection attempt fails.
        """
        source_id = self._config.get("source_id", "unknown")
        connection = None
        try:
            connection = await asyncpg.connect(
                host=self._config["host"],
                port=int(self._config["port"]),
                database=self._config["database"],
                user=self._config["user"],
                password=self._config["password"],
                timeout=timeout,
            )
            # Verify the connection is usable
            await connection.fetchval("SELECT 1")
            logger.info(
                "PostgreSQL connection test succeeded",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "host": self._config["host"],
                    "database": self._config["database"],
                },
            )
            return True
        except (
            asyncpg.PostgresError,
            asyncpg.InterfaceError,
            OSError,
            TimeoutError,
        ) as error:
            logger.warning(
                "PostgreSQL connection test failed",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "host": self._config["host"],
                    "database": self._config["database"],
                    "error": str(error),
                },
            )
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Failed to connect to PostgreSQL: {error}",
                detail=f"source_id={source_id}, operation=test_connection",
            ) from error
        finally:
            if connection is not None:
                await connection.close()

    async def discover_metadata(self) -> SourceMetadata:
        """Discover source-level metadata from the PostgreSQL instance.

        NOTE: Full implementation deferred to Phase 1.

        Raises:
            NotImplementedError: Always — stub implementation.
        """
        raise NotImplementedError(
            "Full PostgreSQL metadata discovery deferred to Phase 1"
        )

    async def discover_schema(self) -> SchemaInfo:
        """Discover table and column schema from the PostgreSQL database.

        NOTE: Full implementation deferred to Phase 1.

        Raises:
            NotImplementedError: Always — stub implementation.
        """
        raise NotImplementedError(
            "Full PostgreSQL schema discovery deferred to Phase 1"
        )

    async def execute_read(self, query: SourceQuery) -> QueryResult:
        """Execute a read-only SQL query against the PostgreSQL database.

        Accepts parameterized SQL strings as the native query format.

        NOTE: Full implementation deferred to Phase 1.

        Args:
            query: A SQL string (parameterized) to execute.

        Raises:
            NotImplementedError: Always — stub implementation.
        """
        raise NotImplementedError(
            "Full PostgreSQL query execution deferred to Phase 1"
        )
