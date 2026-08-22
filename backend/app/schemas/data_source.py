"""
Data source request and response schemas.

Defines typed contracts for data source API endpoints,
including CRUD operations, connection testing, and credential masking.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    """Request schema for creating a data source."""

    name: str = Field(min_length=1, max_length=255, description="Data source name")
    source_type: str = Field(min_length=1, max_length=50, description="Type of data source (e.g., postgresql, mongodb)")
    display_label: str = Field(min_length=1, max_length=255, description="Human-readable label for display")
    connection_config: dict = Field(default_factory=dict, description="Connection parameters (sensitive fields will be encrypted)")


class DataSourceUpdate(BaseModel):
    """Partial update schema for data sources.

    connection_config SEMANTICS: When provided, connection_config is treated
    as a COMPLETE REPLACEMENT of the existing config — NOT a deep merge.
    The entire new config is encrypted and stored, replacing the previous one.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Data source name")
    display_label: str | None = Field(default=None, min_length=1, max_length=255, description="Human-readable label")
    connection_config: dict | None = Field(default=None, description="Complete replacement config — not merged with existing")
    connection_status: str | None = Field(default=None, max_length=50, description="Connection status")


class DataSourceResponse(BaseModel):
    """Response schema for a data source.

    connection_config contains NON-SENSITIVE parameters only (host, port, database, etc.).
    Sensitive credentials are represented as explicit *_configured boolean fields.
    """

    id: UUID
    name: str
    source_type: str
    display_label: str
    connection_config: dict = Field(description="Non-sensitive params + *_configured booleans from mask_config")
    connection_status: str
    last_connected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestConnectionResponse(BaseModel):
    """Response schema for data source connection test."""

    success: bool = Field(description="Whether the connection test succeeded")
    source_type: str = Field(description="Type of the data source tested")
    source_name: str = Field(description="Name of the data source tested")
    message: str = Field(description="Human-readable result message")
    request_id: str = Field(description="Request identifier for traceability")
