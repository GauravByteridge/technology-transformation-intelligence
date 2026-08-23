"""
DataSourceConnector protocol and supporting types.

Defines the capability-based interface that all external data source
connectors must implement. Each connector provides connection testing,
metadata discovery, schema discovery, and read-only query execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Union


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceMetadata:
    """Source-level metadata returned by discover_metadata().

    Attributes:
        source_type: Identifier such as 'postgresql' or 'mongodb'.
        name: Human-readable name of the data source.
        version: Version string of the external system (e.g. '15.2').
        properties: Arbitrary additional metadata key/value pairs.
    """

    source_type: str
    name: str
    version: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FieldInfo:
    """Describes a single field (column) within a table or collection.

    Attributes:
        name: Field/column name.
        field_type: Data type as reported by the source (e.g. 'integer', 'string').
        nullable: Whether the field accepts null values.
    """

    name: str
    field_type: str
    nullable: bool = True


@dataclass(frozen=True)
class TableSchema:
    """Schema information for a single table or collection.

    Attributes:
        name: Table or collection name.
        fields: Ordered list of field descriptors.
    """

    name: str
    fields: list[FieldInfo] = field(default_factory=list)


@dataclass(frozen=True)
class SchemaInfo:
    """Complete schema information for a data source.

    Attributes:
        tables: List of table/collection schemas discovered in the source.
    """

    tables: list[TableSchema] = field(default_factory=list)


# NOTE: SourceQuery uses a Union to accommodate different query languages.
# SQL-based sources use a string query; document-based sources (MongoDB) use a dict.
SourceQuery = Union[str, dict[str, Any]]
"""Query representation flexible enough for SQL (str) or MongoDB (dict)."""


@dataclass(frozen=True)
class QueryResult:
    """Typed result of execute_read().

    Attributes:
        columns: Column/field names in result order.
        rows: List of row dicts mapping column names to values.
        row_count: Number of rows returned.
        source_type: Connector type that produced these results.
        has_more_rows: Whether the result was truncated by the row cap.
    """

    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    source_type: str = ""
    has_more_rows: bool = False


# ---------------------------------------------------------------------------
# DataSourceConnector protocol
# ---------------------------------------------------------------------------


class DataSourceConnector(Protocol):
    """Capability-based protocol for external data source connectors.

    Implementations provide read-only access to structured external databases.
    Each connector accepts source-native query formats — the platform does not
    force all sources into a single query language.
    """

    async def test_connection(self, timeout: int = 10) -> bool:
        """Attempt to connect to the data source.

        Args:
            timeout: Maximum seconds to wait for a connection response.

        Returns:
            True if the connection succeeds, False otherwise.
        """
        ...

    async def discover_metadata(self) -> SourceMetadata:
        """Return source-level metadata (type, name, version, properties)."""
        ...

    async def discover_schema(self) -> SchemaInfo:
        """Return table/collection names, field names, and field types."""
        ...

    async def execute_read(self, query: SourceQuery) -> QueryResult:
        """Execute a read-only query against the data source.

        Args:
            query: Source-appropriate query — SQL string for relational DBs,
                   MongoDB-style dict for document stores.

        Returns:
            Typed query results with column names and row data.
        """
        ...
