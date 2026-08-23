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
import re
from typing import Any

import asyncpg

from app.connectors.protocol import (
    FieldInfo,
    QueryResult,
    SchemaInfo,
    SourceMetadata,
    SourceQuery,
    TableSchema,
)
from app.connectors.sanitizer import sanitize_message
from app.connectors.sql_validator import validate_read_only_sql
from app.errors.datasource_errors import (
    DataSourceConnectionError,
    QueryExecutionError,
    SchemaDiscoveryError,
)

logger = logging.getLogger(__name__)

# Connection config keys
_REQUIRED_CONFIG_KEYS = ("host", "port", "database", "user", "password")

# Sensitive property keys to exclude from metadata responses.
# Mirrors SENSITIVE_FIELDS in app/security/credential_encryptor.py.
_SENSITIVE_PROPERTY_KEYS: frozenset[str] = frozenset(
    {"password", "token", "secret", "api_key", "private_key"}
)

# Matches credential-bearing connection URIs (postgresql://user:pass@host, mongodb://user:pass@host)
_CREDENTIAL_URI_PATTERN: re.Pattern[str] = re.compile(
    r"(postgresql|mongodb)(\+\w+|\+srv)?://\S+:\S+@"
)


class PostgresConnector:
    """PostgreSQL connector with read-only access via asyncpg.

    Implements the DataSourceConnector protocol. Accepts parameterized
    SQL strings as the native query format.

    Args:
        connection_config: Dict with keys: host, port, database, user, password.
        row_limit: Maximum rows to return from execute_read (1–100000, default 1000).
        connection_timeout: Seconds to wait for connection (1–60, default 10).

    Security:
        Read-only access is enforced by:
        - Only exposing `execute_read()` (no write operations in the interface)
        - Requiring that database credentials have SELECT-only grants
        - The platform does NOT implement a SQL parser or query security engine;
          database-level permissions are the enforcement mechanism
    """

    # DESIGN DECISION (Task 4.1): Row-Limit Enforcement Strategy
    #
    # We use asyncpg's connection.fetch() with the user's SQL UNMODIFIED,
    # then slice to row_limit + 1 in Python. This avoids query wrapping
    # (SELECT * FROM (user_sql) AS _q LIMIT N) which has edge cases with
    # ORDER BY optimization push-down and complex queries.
    #
    # Alternatives considered:
    # 1. Query wrapping: SELECT * FROM (<user_sql>) AS _q LIMIT N
    #    - Works for most cases but PostgreSQL may not push down LIMIT
    #      optimization for complex queries, and wrapping CTEs/UNION/ORDER BY
    #      introduces subtle semantic differences.
    # 2. asyncpg cursors with cursor.forward() / fetch batches
    #    - Only fetches needed rows but adds cursor management complexity.
    #
    # Chosen approach: fetch unmodified query, slice in Python to row_limit + 1
    #
    # Trade-offs:
    # - All result rows transfer over the wire before Python-side truncation
    # - For POC row_limit of 1000, this overhead is acceptable
    # - statement_timeout protects against queries returning millions of rows
    # - SET TRANSACTION READ ONLY prevents writes regardless of query content
    # - The limit+1 pattern enables deterministic truncation detection
    #   (has_more_rows = len(fetched) > row_limit)
    #
    # Future optimization: server-side cursors with fetch(n) for large limits.

    SOURCE_TYPE = "postgresql"

    def __init__(
        self,
        connection_config: dict[str, Any],
        *,
        row_limit: int = 1000,
        connection_timeout: int = 10,
    ) -> None:
        if not (1 <= row_limit <= 100_000):
            raise ValueError(
                f"row_limit must be between 1 and 100000, got {row_limit}"
            )
        if not (1 <= connection_timeout <= 60):
            raise ValueError(
                f"connection_timeout must be between 1 and 60, got {connection_timeout}"
            )
        self._config = connection_config
        self._row_limit = row_limit
        self._connection_timeout = connection_timeout
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

    def _filter_sensitive_properties(self, properties: dict) -> dict:
        """Remove sensitive fields from a properties dictionary.

        Excludes keys matching SENSITIVE_FIELDS (case-insensitive) and values
        containing credential-bearing URI patterns (postgresql://user:pass@host,
        mongodb://user:pass@host).

        Returns a new dict — does not mutate the input.
        """
        return {
            key: value
            for key, value in properties.items()
            if key.lower() not in _SENSITIVE_PROPERTY_KEYS
            and not (
                isinstance(value, str) and _CREDENTIAL_URI_PATTERN.search(value)
            )
        }

    async def test_connection(self, timeout: int | None = None) -> bool:
        """Attempt a real connection to the PostgreSQL database.

        Uses asyncpg to connect with the configured credentials and timeout.
        Returns True on success, raises DataSourceConnectionError on failure.

        Args:
            timeout: Maximum seconds to wait for connection. If None, uses
                the instance's configured connection_timeout.

        Returns:
            True if the connection succeeds.

        Raises:
            DataSourceConnectionError: If the connection attempt fails.
        """
        effective_timeout = timeout if timeout is not None else self._connection_timeout
        source_id = self._config.get("source_id", "unknown")
        connection = None
        try:
            connection = await asyncpg.connect(
                host=self._config["host"],
                port=int(self._config["port"]),
                database=self._config["database"],
                user=self._config["user"],
                password=self._config["password"],
                timeout=effective_timeout,
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
                    "error": sanitize_message(str(error)),
                },
            )
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Failed to connect to PostgreSQL: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=test_connection",
            ) from error
        finally:
            if connection is not None:
                await connection.close()

    async def discover_metadata(self) -> SourceMetadata:
        """Discover source-level metadata from the PostgreSQL instance.

        Queries the server version and non-sensitive configuration properties.
        Connection is always closed in the finally block.

        Returns:
            SourceMetadata with source_type, database name, version, and
            filtered properties.

        Raises:
            DataSourceConnectionError: If the PostgreSQL instance is unreachable.
            SchemaDiscoveryError: If a database error occurs during discovery.
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
                timeout=self._connection_timeout,
            )

            # Retrieve server version string
            version_str = await connection.fetchval("SELECT version()")

            # Retrieve non-sensitive server properties
            rows = await connection.fetch(
                "SELECT name, setting FROM pg_settings "
                "WHERE name IN ('max_connections', 'server_encoding', "
                "'TimeZone', 'shared_buffers')"
            )
            properties = {row["name"]: row["setting"] for row in rows}
            filtered_props = self._filter_sensitive_properties(properties)

            logger.info(
                "PostgreSQL metadata discovery succeeded",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "database": self._config["database"],
                },
            )

            return SourceMetadata(
                source_type=self.SOURCE_TYPE,
                name=self._config["database"],
                version=version_str or "",
                properties=filtered_props,
            )
        except (asyncpg.InterfaceError, OSError, TimeoutError) as error:
            logger.warning(
                "PostgreSQL metadata discovery connection failed",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "database": self._config["database"],
                    "error": sanitize_message(str(error)),
                },
            )
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Failed to connect to PostgreSQL during metadata discovery: "
                f"{sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=discover_metadata",
            ) from error
        except asyncpg.PostgresError as error:
            logger.warning(
                "PostgreSQL metadata discovery database error",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "database": self._config["database"],
                    "error": sanitize_message(str(error)),
                },
            )
            raise SchemaDiscoveryError(
                source_type=self.SOURCE_TYPE,
                message=f"Metadata discovery failed: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=discover_metadata",
            ) from error
        finally:
            if connection is not None:
                await connection.close()

    async def discover_schema(self) -> SchemaInfo:
        """Discover table and column schema from the PostgreSQL database.

        Queries information_schema for BASE TABLE objects and their columns.
        Excludes system schemas (pg_catalog, information_schema, pg_toast).
        Supports optional schema filtering via "schema" key in connection_config.

        Returns:
            SchemaInfo with schema-qualified table names ("schema.table" format).

        Raises:
            DataSourceConnectionError: If the PostgreSQL instance is unreachable.
            SchemaDiscoveryError: If a database error occurs during discovery.
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
                timeout=self._connection_timeout,
            )

            # Build query to discover tables
            schema_filter = self._config.get("schema")

            if schema_filter:
                # Filter to specific schema
                table_query = """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                    AND table_schema = $1
                    ORDER BY table_schema, table_name
                """
                table_rows = await connection.fetch(table_query, schema_filter)
            else:
                # All schemas except system schemas
                table_query = """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                    AND table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                    ORDER BY table_schema, table_name
                """
                table_rows = await connection.fetch(table_query)

            # For each table, get columns ordered by ordinal_position
            tables: list[TableSchema] = []
            for table_row in table_rows:
                schema_name = table_row["table_schema"]
                table_name = table_row["table_name"]
                qualified_name = f"{schema_name}.{table_name}"

                column_query = """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = $1 AND table_name = $2
                    ORDER BY ordinal_position
                """
                column_rows = await connection.fetch(
                    column_query, schema_name, table_name
                )

                fields = [
                    FieldInfo(
                        name=col["column_name"],
                        field_type=col["data_type"],
                        nullable=(col["is_nullable"] == "YES"),
                    )
                    for col in column_rows
                ]

                tables.append(TableSchema(name=qualified_name, fields=fields))

            logger.info(
                "PostgreSQL schema discovery succeeded",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "database": self._config["database"],
                    "table_count": len(tables),
                },
            )

            return SchemaInfo(tables=tables)

        except (asyncpg.InterfaceError, OSError, TimeoutError) as error:
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Connection failed during schema discovery: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=discover_schema",
            ) from error
        except asyncpg.PostgresError as error:
            raise SchemaDiscoveryError(
                source_type=self.SOURCE_TYPE,
                message=f"Schema discovery failed: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=discover_schema",
            ) from error
        finally:
            if connection is not None:
                await connection.close()

    async def execute_read(
        self, query: SourceQuery, *, timeout_budget: float | None = None
    ) -> QueryResult:
        """Execute a read-only SQL query against the PostgreSQL database.

        Defense-in-depth:
          Layer 1: validate_read_only_sql() rejects prohibited SQL early.
          Layer 2: SET TRANSACTION READ ONLY enforced by PostgreSQL — blocks
                   all write attempts including data-modifying CTEs.

        Args:
            query: A SQL string to execute read-only.
            timeout_budget: Remaining seconds from the API operation budget.
                If provided, sets PostgreSQL statement_timeout to prevent
                long-running queries. Owned by ConnectorService — connectors
                do NOT independently track a 30s timer.

        Returns:
            QueryResult with columns, rows, row_count, and truncation info.

        Raises:
            QueryValidationError: If SQL is empty, multi-statement, or starts
                with a prohibited keyword (propagates to API as 400).
            QueryExecutionError: If the query attempts a write operation or
                encounters a database error during execution.
            DataSourceConnectionError: If the PostgreSQL instance is unreachable.
        """
        # Layer 1: Application-level early rejection
        validate_read_only_sql(str(query), source_type=self.SOURCE_TYPE)

        source_id = self._config.get("source_id", "unknown")
        connection = None
        try:
            connection = await asyncpg.connect(
                host=self._config["host"],
                port=int(self._config["port"]),
                database=self._config["database"],
                user=self._config["user"],
                password=self._config["password"],
                timeout=self._connection_timeout,
            )

            # Layer 2: PostgreSQL session-level read-only (PRIMARY enforcement)
            await connection.execute("SET TRANSACTION READ ONLY")

            # Set statement_timeout using remaining API budget (propagated from
            # ConnectorService). This ensures PostgreSQL cancels the query before
            # the API-level asyncio.wait_for fires, providing a cleaner error.
            if timeout_budget is not None:
                remaining_ms = max(int(timeout_budget * 1000), 1)
                await connection.execute(
                    f"SET statement_timeout = '{remaining_ms}ms'"
                )

            # Execute unmodified query, fetch all rows
            rows = await connection.fetch(str(query))

            # Truncation detection: fetch row_limit+1 to detect overflow
            has_more_rows = len(rows) > self._row_limit
            result_rows = rows[: self._row_limit]

            # Build column names from Record attributes
            columns = list(result_rows[0].keys()) if result_rows else []

            # Convert asyncpg Records to list of dicts
            rows_as_dicts = [dict(row) for row in result_rows]

            return QueryResult(
                columns=columns,
                rows=rows_as_dicts,
                row_count=len(rows_as_dicts),
                source_type=self.SOURCE_TYPE,
                has_more_rows=has_more_rows,
            )
        except asyncpg.exceptions.ReadOnlySQLTransactionError as error:
            raise QueryExecutionError(
                source_type=self.SOURCE_TYPE,
                message="Query attempted a write operation in a read-only transaction",
                detail=f"source_id={source_id}, operation=execute_read",
            ) from error
        except (asyncpg.InterfaceError, OSError, TimeoutError) as error:
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Connection failed during query execution: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=execute_read",
            ) from error
        except asyncpg.PostgresError as error:
            raise QueryExecutionError(
                source_type=self.SOURCE_TYPE,
                message=f"Query execution failed: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=execute_read",
            ) from error
        finally:
            if connection is not None:
                await connection.close()
