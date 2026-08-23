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
"""

from __future__ import annotations

import logging
import re
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import (
    ConnectionFailure,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from app.connectors.protocol import (
    FieldInfo,
    QueryResult,
    SchemaInfo,
    SourceMetadata,
    SourceQuery,
    TableSchema,
)
from app.connectors.sanitizer import sanitize_message
from app.errors.datasource_errors import (
    DataSourceConnectionError,
    QueryExecutionError,
    QueryValidationError,
    SchemaDiscoveryError,
)

logger = logging.getLogger(__name__)

_REQUIRED_CONFIG_KEYS = ("host", "port", "database")

# Sensitive property keys to exclude from metadata responses.
# Mirrors SENSITIVE_FIELDS in app/security/credential_encryptor.py.
_SENSITIVE_PROPERTY_KEYS: frozenset[str] = frozenset(
    {"password", "token", "secret", "api_key", "private_key"}
)

# Matches credential-bearing connection URIs (postgresql://user:pass@host, mongodb://user:pass@host)
_CREDENTIAL_URI_PATTERN: re.Pattern[str] = re.compile(
    r"(postgresql|mongodb)(\+\w+|\+srv)?://\S+:\S+@"
)


class MongoDBConnector:
    """MongoDB connector with read-only access via Motor (async pymongo).

    Implements the DataSourceConnector protocol. Accepts MongoDB-native
    query format as a dict with keys: collection, filter, projection, etc.

    Args:
        connection_config: Dict with keys: host, port, database,
            and optionally username and password.
        row_limit: Maximum documents returned per query (1–10000, default: 1000).
        connection_timeout: Seconds to wait when establishing connection (1–60, default: 10).
        sample_size: Documents sampled per collection during schema discovery (1–10000, default: 100).
        max_nesting_depth: Maximum dot-notation depth for nested fields in schema discovery (1–20, default: 5).

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

    # Strict allowlist of permitted keys in MongoDB query dicts
    _ALLOWED_QUERY_KEYS: frozenset[str] = frozenset(
        {"collection", "filter", "projection", "limit", "sort"}
    )

    # Validation ranges for configurable parameters
    _ROW_LIMIT_RANGE = (1, 10_000)
    _CONNECTION_TIMEOUT_RANGE = (1, 60)
    _SAMPLE_SIZE_RANGE = (1, 10_000)
    _MAX_NESTING_DEPTH_RANGE = (1, 20)

    def __init__(
        self,
        connection_config: dict[str, Any],
        *,
        row_limit: int = 1000,
        connection_timeout: int = 10,
        sample_size: int = 100,
        max_nesting_depth: int = 5,
    ) -> None:
        self._validate_parameters(
            row_limit=row_limit,
            connection_timeout=connection_timeout,
            sample_size=sample_size,
            max_nesting_depth=max_nesting_depth,
        )
        self._row_limit = row_limit
        self._connection_timeout = connection_timeout
        self._sample_size = sample_size
        self._max_nesting_depth = max_nesting_depth
        self._config = connection_config
        self._validate_config()

    def _validate_parameters(
        self,
        *,
        row_limit: int,
        connection_timeout: int,
        sample_size: int,
        max_nesting_depth: int,
    ) -> None:
        """Validate that configurable parameters are within allowed ranges.

        Raises:
            ValueError: If any parameter is outside its permitted range.
        """
        checks: list[tuple[str, int, tuple[int, int]]] = [
            ("row_limit", row_limit, self._ROW_LIMIT_RANGE),
            ("connection_timeout", connection_timeout, self._CONNECTION_TIMEOUT_RANGE),
            ("sample_size", sample_size, self._SAMPLE_SIZE_RANGE),
            ("max_nesting_depth", max_nesting_depth, self._MAX_NESTING_DEPTH_RANGE),
        ]
        for name, value, (min_val, max_val) in checks:
            if not isinstance(value, int) or value < min_val or value > max_val:
                raise ValueError(
                    f"{name} must be an integer between {min_val} and {max_val}, got {value!r}"
                )

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

    def _filter_sensitive_properties(self, properties: dict) -> dict:
        """Remove sensitive fields from a properties dictionary.

        Excludes keys matching known sensitive names (case-insensitive) and
        values that contain credential-bearing connection URIs. Returns a new
        dict — the input is not mutated.

        Args:
            properties: Raw properties dictionary from server metadata.

        Returns:
            Filtered copy with sensitive entries removed.
        """
        return {
            key: value
            for key, value in properties.items()
            if key.lower() not in _SENSITIVE_PROPERTY_KEYS
            and not (
                isinstance(value, str) and _CREDENTIAL_URI_PATTERN.search(value)
            )
        }

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
                    "error": sanitize_message(str(error)),
                },
            )
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Failed to connect to MongoDB: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=test_connection",
            ) from error
        finally:
            if client is not None:
                client.close()

    async def discover_metadata(self) -> SourceMetadata:
        """Discover source-level metadata from the MongoDB instance.

        Connects to MongoDB, issues the serverInfo command, extracts
        version and properties, filters sensitive fields, and returns
        a SourceMetadata object.

        Returns:
            SourceMetadata with source_type, name, version, and filtered properties.

        Raises:
            DataSourceConnectionError: If the MongoDB instance is unreachable
                or the connection timeout is exceeded.
            SchemaDiscoveryError: If a non-connection database error occurs
                (e.g., OperationFailure from the serverInfo command).
        """
        source_id = self._config.get("source_id", "unknown")
        client = None
        try:
            uri = self._build_connection_uri()
            client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=self._connection_timeout * 1000,
                connectTimeoutMS=self._connection_timeout * 1000,
            )
            database = client[self._config["database"]]
            server_info = await database.command("serverInfo")

            version = server_info.get("version", "")
            filtered_props = self._filter_sensitive_properties(server_info)

            logger.info(
                "MongoDB metadata discovery succeeded",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "host": self._config["host"],
                    "database": self._config["database"],
                    "version": version,
                },
            )

            return SourceMetadata(
                source_type=self.SOURCE_TYPE,
                name=self._config["database"],
                version=version,
                properties=filtered_props,
            )
        except (
            ConnectionFailure,
            ServerSelectionTimeoutError,
            OSError,
            TimeoutError,
        ) as error:
            logger.warning(
                "MongoDB metadata discovery failed — connection error",
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
                message=f"Failed to connect to MongoDB during metadata discovery: "
                f"{sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=discover_metadata",
            ) from error
        except OperationFailure as error:
            logger.warning(
                "MongoDB metadata discovery failed — operation error",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "host": self._config["host"],
                    "database": self._config["database"],
                    "error": sanitize_message(str(error)),
                },
            )
            raise SchemaDiscoveryError(
                source_type=self.SOURCE_TYPE,
                message=f"MongoDB metadata discovery failed: "
                f"{sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=discover_metadata",
            ) from error
        finally:
            if client is not None:
                client.close()

    def _infer_field_type(self, values: list) -> str:
        """Deterministic BSON type inference from sampled field values.

        Maps each value to its type string and returns the single type if
        uniform, or "mixed" when multiple types are present.

        Type mapping:
        - str → "string"
        - bool → "bool" (checked before int — bool is a subclass of int in Python)
        - int → "int"
        - float → "double"
        - list → "array"
        - dict → "object"
        - ObjectId → "objectId"
        - datetime → "date"
        - None → "null"
        - Decimal128 → "decimal"
        - bytes → "binary"
        - Unknown types → "object" (fallback)

        Args:
            values: List of sampled field values from documents.

        Returns:
            A single type string if all non-None values share the same type,
            "mixed" if multiple types are present, or "null" if the list is empty.
        """
        from bson import Decimal128, ObjectId
        from datetime import datetime

        types_seen: set[str] = set()

        for value in values:
            if value is None:
                types_seen.add("null")
            elif isinstance(value, bool):  # Must check before int!
                types_seen.add("bool")
            elif isinstance(value, int):
                types_seen.add("int")
            elif isinstance(value, float):
                types_seen.add("double")
            elif isinstance(value, str):
                types_seen.add("string")
            elif isinstance(value, list):
                types_seen.add("array")
            elif isinstance(value, dict):
                types_seen.add("object")
            elif isinstance(value, ObjectId):
                types_seen.add("objectId")
            elif isinstance(value, datetime):
                types_seen.add("date")
            elif isinstance(value, Decimal128):
                types_seen.add("decimal")
            elif isinstance(value, bytes):
                types_seen.add("binary")
            else:
                types_seen.add("object")  # fallback for unknown types

        if len(types_seen) == 0:
            return "null"
        if len(types_seen) == 1:
            return types_seen.pop()
        return "mixed"

    def _expand_nested_fields(
        self, documents: list[dict], max_depth: int
    ) -> list[FieldInfo]:
        """Extract fields from sampled documents using dot notation for nested fields.

        Nested dicts at depth <= max_depth are expanded (e.g., "address.city").
        Nested dicts at depth > max_depth are NOT expanded and are represented
        as field_type "object". Arrays are represented as "array" without
        element-type inference.

        For each field path: collects all values across documents, infers the
        type via _infer_field_type, and determines nullable based on presence
        across the full document set.

        Args:
            documents: List of sampled MongoDB documents.
            max_depth: Maximum nesting depth for dot-notation expansion.

        Returns:
            Sorted list of FieldInfo objects with name, field_type, nullable.
        """
        field_values: dict[str, list] = {}
        field_presence: dict[str, int] = {}
        total_docs = len(documents)

        def _extract_fields(obj: dict, prefix: str, current_depth: int) -> None:
            for key, value in obj.items():
                path = f"{prefix}.{key}" if prefix else key

                if path not in field_values:
                    field_values[path] = []
                    field_presence[path] = 0

                field_presence[path] += 1

                if isinstance(value, dict) and current_depth < max_depth:
                    # Expand nested dict — recurse deeper
                    _extract_fields(value, path, current_depth + 1)
                else:
                    # Terminal value or max depth reached for dicts
                    field_values[path].append(value)

        for doc in documents:
            _extract_fields(doc, "", 1)

        fields: list[FieldInfo] = []
        for path in sorted(field_values.keys()):
            values = field_values[path]
            if not values:
                continue

            field_type = self._infer_field_type(values)
            # Nullable when the field is absent from at least one document
            nullable = field_presence.get(path, 0) < total_docs

            fields.append(
                FieldInfo(name=path, field_type=field_type, nullable=nullable)
            )

        return fields

    async def discover_schema(self) -> SchemaInfo:
        """Discover collection and field schema from the MongoDB database.

        Lists collections (excluding system.* prefix), samples documents from each,
        infers field types using dot notation for nested fields up to max_nesting_depth.
        Empty collections produce a TableSchema with empty fields list.

        Returns:
            SchemaInfo with table schemas for each user collection.

        Raises:
            DataSourceConnectionError: If the MongoDB instance is unreachable
                or the connection timeout is exceeded.
            SchemaDiscoveryError: If a non-connection database error occurs
                during schema discovery.
        """
        source_id = self._config.get("source_id", "unknown")
        client = None
        try:
            uri = self._build_connection_uri()
            client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=self._connection_timeout * 1000,
                connectTimeoutMS=self._connection_timeout * 1000,
            )
            database = client[self._config["database"]]

            # List all collections, filter out system collections
            all_collections = await database.list_collection_names()
            user_collections = [
                name for name in all_collections
                if not name.startswith("system.")
            ]

            tables: list[TableSchema] = []
            for collection_name in sorted(user_collections):
                collection = database[collection_name]

                # Sample documents (use all if fewer than sample_size)
                cursor = collection.find().limit(self._sample_size)
                documents = await cursor.to_list(length=self._sample_size)

                if not documents:
                    # Empty collection → empty fields list
                    tables.append(TableSchema(name=collection_name, fields=[]))
                else:
                    # Infer fields using dot notation expansion
                    fields = self._expand_nested_fields(
                        documents, self._max_nesting_depth
                    )
                    tables.append(TableSchema(name=collection_name, fields=fields))

            logger.info(
                "MongoDB schema discovery succeeded",
                extra={
                    "source_id": source_id,
                    "source_type": self.SOURCE_TYPE,
                    "host": self._config["host"],
                    "database": self._config["database"],
                    "collection_count": len(tables),
                },
            )

            return SchemaInfo(tables=tables)

        except (
            ConnectionFailure,
            ServerSelectionTimeoutError,
            OSError,
            TimeoutError,
        ) as error:
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Connection failed during schema discovery: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=discover_schema",
            ) from error
        except OperationFailure as error:
            raise SchemaDiscoveryError(
                source_type=self.SOURCE_TYPE,
                message=f"Schema discovery failed: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=discover_schema",
            ) from error
        finally:
            if client is not None:
                client.close()

    # DESIGN DECISION (Task 7.1): MongoDB Sort Validation
    #
    # Sort validation uses partial application-side validation:
    # - Verify "sort" value is a dict (catches type errors early)
    # - Delegate key/value semantics to Motor/MongoDB
    #   (e.g., sort field names and direction values 1/-1)
    # - Invalid sort content results in MongoDB OperationFailure
    #   which maps to QueryExecutionError → HTTP 502
    #
    # This is consistent with how "filter" and "projection" are handled:
    # structure validated, semantics delegated to the database driver.

    def _validate_query(self, query: dict) -> None:
        """Validate MongoDB query dict against strict key allowlist.

        Raises QueryValidationError if:
        - query is not a dict
        - "collection" key is missing
        - Any key is not in _ALLOWED_QUERY_KEYS
        - "sort" is present but not a dict (per design decision 7.1: partial validation)
        """
        if not isinstance(query, dict):
            raise QueryValidationError(
                source_type=self.SOURCE_TYPE,
                message="MongoDB query must be a dictionary",
            )

        if "collection" not in query:
            raise QueryValidationError(
                source_type=self.SOURCE_TYPE,
                message="MongoDB query must include 'collection' key",
            )

        invalid_keys = set(query.keys()) - self._ALLOWED_QUERY_KEYS
        if invalid_keys:
            raise QueryValidationError(
                source_type=self.SOURCE_TYPE,
                message=f"Unsupported query keys: {sorted(invalid_keys)}. "
                f"Permitted keys: {sorted(self._ALLOWED_QUERY_KEYS)}",
            )

        # Partial sort validation (design decision 7.1): verify type only
        if "sort" in query and not isinstance(query["sort"], dict):
            raise QueryValidationError(
                source_type=self.SOURCE_TYPE,
                message="'sort' must be a dictionary (e.g., {\"field\": 1} or {\"field\": -1})",
            )

    async def execute_read(self, query: SourceQuery) -> QueryResult:
        """Execute a read-only find operation against MongoDB.

        Only find operations are supported via the strict query key allowlist.
        Aggregation pipelines, arbitrary commands, and write operations are rejected.

        Args:
            query: A dict with MongoDB-native query parameters.
                Required: "collection".
                Optional: "filter", "projection", "sort", "limit".

        Returns:
            QueryResult with columns, rows, row_count, source_type, and has_more_rows.

        Raises:
            QueryValidationError: If query structure is invalid.
            DataSourceConnectionError: If MongoDB is unreachable.
            QueryExecutionError: If the query fails at the database level.
        """
        if not isinstance(query, dict):
            raise QueryValidationError(
                source_type=self.SOURCE_TYPE,
                message="MongoDB query must be a dictionary",
            )
        self._validate_query(query)

        source_id = self._config.get("source_id", "unknown")
        client = None
        try:
            uri = self._build_connection_uri()
            client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=self._connection_timeout * 1000,
                connectTimeoutMS=self._connection_timeout * 1000,
            )
            database = client[self._config["database"]]
            collection = database[query["collection"]]

            # Build find operation parameters
            filter_doc = query.get("filter", {})
            projection = query.get("projection")
            sort_spec = query.get("sort")
            user_limit = query.get("limit")

            # Effective limit: min of user-specified and connector row_limit
            effective_limit = self._row_limit
            if user_limit is not None:
                effective_limit = min(int(user_limit), self._row_limit)

            # Fetch limit+1 for truncation detection
            fetch_limit = effective_limit + 1

            # Build cursor
            cursor = collection.find(filter_doc, projection)
            if sort_spec:
                cursor = cursor.sort(list(sort_spec.items()))
            cursor = cursor.limit(fetch_limit)

            # Execute query
            documents = await cursor.to_list(length=fetch_limit)

            # Truncation detection
            has_more_rows = len(documents) > effective_limit
            result_docs = documents[:effective_limit]

            # Serialize documents (ObjectId → string, etc.)
            serialized = [self._serialize_document(doc) for doc in result_docs]

            # Derive columns from all documents preserving insertion order
            columns: list[str] = []
            if serialized:
                seen: set[str] = set()
                for doc in serialized:
                    for key in doc.keys():
                        if key not in seen:
                            seen.add(key)
                            columns.append(key)

            return QueryResult(
                columns=columns,
                rows=serialized,
                row_count=len(serialized),
                source_type=self.SOURCE_TYPE,
                has_more_rows=has_more_rows,
            )
        except (ConnectionFailure, ServerSelectionTimeoutError, OSError, TimeoutError) as error:
            raise DataSourceConnectionError(
                source_type=self.SOURCE_TYPE,
                message=f"Connection failed during query execution: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=execute_read",
            ) from error
        except OperationFailure as error:
            raise QueryExecutionError(
                source_type=self.SOURCE_TYPE,
                message=f"Query execution failed: {sanitize_message(str(error))}",
                detail=f"source_id={source_id}, operation=execute_read",
            ) from error
        finally:
            if client is not None:
                client.close()

    def _serialize_document(self, doc: dict) -> dict:
        """Serialize a MongoDB document for JSON output.

        Converts non-JSON-serializable BSON types to their string/JSON-safe
        forms. Nested dicts and lists are recursed.

        Guaranteed conversions (from requirement 6.10):
        - ObjectId → 24-character hex string via str(oid)

        Additional conversions (required for JSON serializability):
        - datetime → ISO 8601 string via isoformat()
        - Decimal128 → string via str()
        - bytes → base64-encoded string
        - Nested dicts are recursed
        - Lists are recursed (each element serialized)

        All other types are passed through (assumed JSON-serializable).

        Args:
            doc: A MongoDB document (dict) to serialize.

        Returns:
            A new dict with all values converted to JSON-safe forms.
        """
        return {key: self._serialize_value(value) for key, value in doc.items()}

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value to a JSON-compatible form.

        Args:
            value: Any value from a MongoDB document.

        Returns:
            A JSON-serializable representation of the value.
        """
        from bson import Decimal128, ObjectId
        from datetime import datetime
        import base64

        if isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, Decimal128):
            return str(value)
        elif isinstance(value, bytes):
            return base64.b64encode(value).decode("utf-8")
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        else:
            return value
