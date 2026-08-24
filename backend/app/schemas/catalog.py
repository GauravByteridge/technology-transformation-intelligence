"""
Catalog request and response schemas.

Defines typed contracts for Enterprise Data Catalog API endpoints,
including catalog entries, project mappings, discovery results,
search requests, and catalog context injection.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CatalogFieldSchema(BaseModel):
    """Schema for a single field within a catalog entry."""

    name: str
    field_type: str
    nullable: bool
    is_primary_key: bool
    semantic_label: str | None = None
    semantic_description: str | None = None
    is_project_field: bool = False
    is_sensitive: bool = False


class ForeignKeyRefSchema(BaseModel):
    """Schema for a foreign key reference between tables."""

    column: str
    references_table: str
    references_column: str


class CatalogEntryResponse(BaseModel):
    """Response schema for a catalog entry.

    Represents a discovered database object (table, collection, view, or document)
    with both technical and semantic metadata.
    """

    entry_id: str
    source_id: str
    source_type: str = Field(
        description="Type of data source: postgresql, mongodb, or document"
    )
    source_name: str
    database_name: str | None = None
    schema_name: str | None = None
    object_name: str
    object_type: str = Field(
        description="Object type: table, collection, view, or document"
    )
    fields: list[CatalogFieldSchema] = Field(default_factory=list)
    primary_keys: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKeyRefSchema] = Field(default_factory=list)
    indexes: list[str] = Field(default_factory=list)
    semantic_name: str | None = None
    semantic_description: str | None = None
    domain_tags: list[str] = Field(default_factory=list)
    query_capabilities: list[str] = Field(default_factory=list)
    suggested_queries: list[str] = Field(default_factory=list)
    confidence: str = Field(
        default="medium",
        description="Confidence level: high, medium, or low",
    )
    project_fields: list[str] = Field(default_factory=list)
    version: int = 1
    discovered_at: datetime

    model_config = {"from_attributes": True}


class ProjectMappingSchema(BaseModel):
    """Schema for a project-to-catalog-entry mapping."""

    id: str
    project_id: str
    source_id: str
    catalog_entry_id: str
    project_field: str = Field(
        description="Field name used for project filtering"
    )
    mapping_type: str = Field(
        description="How the mapping was established: discovered or configured"
    )
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoveryResultResponse(BaseModel):
    """Response schema for a discovery operation result."""

    source_id: str
    success: bool
    objects_discovered: int = 0
    fields_discovered: int = 0
    relationships_discovered: int = 0
    project_fields_found: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    error: str | None = None
    discovered_at: datetime


class CatalogSearchRequest(BaseModel):
    """Request schema for searching the catalog."""

    query: str = Field(
        min_length=1,
        description="Natural-language search query",
    )
    project_id: str | None = Field(
        default=None,
        description="Optional project ID to scope search results",
    )


class CatalogContextSchema(BaseModel):
    """Schema for catalog context injected into AI agent prompts.

    Contains a curated subset of catalog entries relevant to the current
    question and project context.
    """

    entries: list[CatalogEntryResponse] = Field(default_factory=list)
    project_id: str | None = None
    total_available: int = 0
    included_count: int = 0
