"""
Executive brief request/response schemas.

Defines Pydantic models for brief generation, listing, and detail views.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BriefSourceResponse(BaseModel):
    """Response schema for a brief source."""

    id: UUID
    evidence_id: UUID | None = None
    query_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExecutiveBriefCreate(BaseModel):
    """Request schema for generating an executive brief."""

    project_id: UUID = Field(description="Project to generate brief for")
    title: str = Field(min_length=1, max_length=500, description="Brief title")


class ExecutiveBriefResponse(BaseModel):
    """Response schema for an executive brief."""

    id: UUID
    project_id: UUID
    title: str
    summary: str | None = None
    content: dict | None = None
    generated_by_query: UUID | None = None
    status: str
    created_by: UUID
    sources: list[BriefSourceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExecutiveBriefListResponse(BaseModel):
    """Response schema for listing briefs (lighter payload)."""

    id: UUID
    project_id: UUID
    title: str
    summary: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
