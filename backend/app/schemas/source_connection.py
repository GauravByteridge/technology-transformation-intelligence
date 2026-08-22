"""
Source connection request/response schemas.

Defines Pydantic models for the project-to-data-source relationship operations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SourceConnectionCreate(BaseModel):
    """Request schema for linking a data source to a project."""

    data_source_id: UUID = Field(description="Data source to connect to the project")
    purpose: str = Field(min_length=1, max_length=255, description="Purpose of this connection")


class SourceConnectionResponse(BaseModel):
    """Response schema for a project-to-data-source connection."""

    id: UUID
    project_id: UUID
    data_source_id: UUID
    purpose: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
