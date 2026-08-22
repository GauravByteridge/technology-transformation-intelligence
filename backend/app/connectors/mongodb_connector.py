"""
MongoDB connector implementing the DataSourceConnector protocol.

Provides read-only access to MongoDB databases using the Motor async driver
for connection management and query execution.

Security Model — Read-Only Access Enforcement:
    1. Only `execute_read()` is exposed in the DataSourceConnector interface.
       There are no write methods (insert, update, delete) available.
    2. External MongoDB credentials MUST be configured with database-level
       read-only permissions (e.g., a MongoDB user with the `read` role only).
    3. The platform does NOT implement a custom query validator — MongoDB's
       role-based access control is the sole enforcement mechanism.

WARNING: Do not configure this connector with credentials that have write access.
         Always use a dedicated MongoDB user with the `read` role.

NOTE: Full query execution is deferred to Phase 1. Currently only
      `test_connection()` performs a real operation; other methods raise
      NotImplementedError.
"""

from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import (
    ConnectionFailure,
    OperationFailure,
    ServerSelectionTimeoutError,
)

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

_REQUIRED_CONFIG_KEYS = ("host", "port", "database")


class MongoDBConnector:
    """MongoDB connector with read-only access via Motor (async pymongo).

    Implements the DataSourceConnector protocol. Accepts MongoDB-native
    query format as a dict with keys: collection, filter, projection, etc.

    Args:
        connection_config: Dict with keys: host, port, database,
            and optionally username and password.

    Security:
        Read-only access is enforced by:
        - Only exposing `execute_read()` (no write operations in the interface)
        - Requiring that MongoDB credentials have the `read` role only
        - The platform does NOT implement a custom query validator;
          MongoDB role-based access control is the enforcement mechanism

    Query Format:
        {
            "collection": "resources",
            "filter": {"project": "alpha"},
            "projection": {"_id": 0, "name": 1, "role": 1},
            "limit": 100
        }
    """

    SOURCE_TYPE = "mongodb"

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

    def _build_connection_uri(self) -> str:
        """Build the MongoDB connection URI from configuration.

        Returns:
            MongoDB URI string constructed from host, port,
            and optional username/password.
        """
        host = self._config["host"]
        port = int(self._config["port"])
        username = self._config.get("username")
        password = self._config.get("password")

        if username and password:
            return f"mongodb://{username}:{password}@{host}:{port}"
        return f"mongodb://{host}:{port}"

    async def test_connection(self, timeout: int = 10) -> bool:
        """Attempt a real connection to the MongoDB database.

        Uses Motor (async pymongo) to connect with the configured credentials
        and verifies connectivity by issuing a ping command.

        Args:
            timeout: Maximum seconds to wait for connection (default: 10).

        Returns:
            True if the connection succeeds.

        Raises:
            DataSourceConnectionError: If the connection attempt fails.
        """
        source_id = self._config.get("source_id", "unknown")
        client = None
        try:
            uri = self._build_connection_uri()
            client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=timeout * 1000,
                connectTimeoutMS=timeout * 1000,
            )
            # Verify the connection by issuing a ping command
            database = client[self._config["database"]]
            await database.command("ping")

            logger.info(
                "MongoDB connection test succeeded",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "host": self._config["host"],
                    "database": self._config["database"],
                },
            )
            return True
        except (
            ConnectionFailure,
            ServerSelectionTimeoutError,
            OperationFailure,
            OSError,
            TimeoutError,
        ) as error:
            logger.warning(
                "MongoDB connection test failed",
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
                message=f"Failed to connect to MongoDB: {error}",
                detail=f"source_id={source_id}, operation=test_connection",
            ) from error
        finally:
            if client is not None:
                client.close()

    async def discover_metadata(self) -> SourceMetadata:
        """Discover source-level metadata from the MongoDB instance.

        NOTE: Full implementation deferred to Phase 1.

        Raises:
            NotImplementedError: Always — stub implementation.
        """
        raise NotImplementedError(
            "Full MongoDB metadata discovery deferred to Phase 1"
        )

    async def discover_schema(self) -> SchemaInfo:
        """Discover collection and field schema from the MongoDB database.

        NOTE: Full implementation deferred to Phase 1.

        Raises:
            NotImplementedError: Always — stub implementation.
        """
        raise NotImplementedError(
            "Full MongoDB schema discovery deferred to Phase 1"
        )

    async def execute_read(self, query: SourceQuery) -> QueryResult:
        """Execute a read-only query against the MongoDB database.

        Accepts MongoDB-native query format as a dict with keys:
        - collection (required): Name of the collection to query
        - filter (optional): MongoDB filter document
        - projection (optional): Fields to include/exclude
        - limit (optional): Maximum documents to return

        NOTE: Full implementation deferred to Phase 1.

        Args:
            query: A dict with MongoDB-native query parameters.

        Raises:
            NotImplementedError: Always — stub implementation.
        """
        raise NotImplementedError(
            "Full MongoDB query execution deferred to Phase 1"
        )
