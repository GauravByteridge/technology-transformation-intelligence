"""
Connector framework — protocol, types, registry, and connector implementations.

Public API:
    DataSourceConnector: Protocol all connectors must satisfy.
    ConnectorRegistry: Maps source types to connector classes.
    PostgresConnector: PostgreSQL connector implementation.
    MongoDBConnector: MongoDB connector implementation.
    SourceMetadata, SchemaInfo, FieldInfo, TableSchema: Metadata types.
    SourceQuery, QueryResult: Query/result types.
"""

from app.connectors.mongodb_connector import MongoDBConnector
from app.connectors.postgres_connector import PostgresConnector
from app.connectors.protocol import (
    DataSourceConnector,
    FieldInfo,
    QueryResult,
    SchemaInfo,
    SourceMetadata,
    SourceQuery,
    TableSchema,
)
from app.connectors.registry import ConnectorRegistry
from app.connectors.sanitizer import sanitize_message

__all__ = [
    "ConnectorRegistry",
    "DataSourceConnector",
    "FieldInfo",
    "MongoDBConnector",
    "PostgresConnector",
    "QueryResult",
    "SchemaInfo",
    "SourceMetadata",
    "SourceQuery",
    "TableSchema",
    "sanitize_message",
]
