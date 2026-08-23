"""Request and response schemas for connector API endpoints (Phase 2).

These schemas define the typed API contracts for:
- Schema discovery (GET /data-sources/{id}/schema)
- Metadata discovery (GET /data-sources/{id}/metadata)
- Query execution (POST /data-sources/{id}/query)
"""

from typing import Any

from pydantic import BaseModel, Field


class SchemaFieldResponse(BaseModel):
    """A single field in a table/collection schema."""

    name: str
    field_type: str
    nullable: bool


class TableSchemaResponse(BaseModel):
    """Schema for a single table or collection."""

    name: str
    fields: list[SchemaFieldResponse]


class SchemaDiscoveryResponse(BaseModel):
    """Response for schema discovery endpoint."""

    tables: list[TableSchemaResponse]
    request_id: str


class MetadataResponse(BaseModel):
    """Response for metadata discovery endpoint."""

    source_type: str
    name: str
    version: str
    properties: dict[str, Any]
    request_id: str


class QueryExecutionRequest(BaseModel):
    """Request body for query execution endpoint.

    The query field accepts a generic union (str | dict).
    Source-specific validation occurs AFTER the data source is resolved
    and source_type is known.
    """

    query: str | dict[str, Any] = Field(
        description="SQL string (PostgreSQL) or query dict (MongoDB). "
        "Validated against source-specific rules after resolution."
    )


class QueryExecutionResponse(BaseModel):
    """Response for query execution endpoint."""

    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    source_type: str
    truncated: bool = Field(
        description="True when more rows existed than the response limit (10000)"
    )
    request_id: str
