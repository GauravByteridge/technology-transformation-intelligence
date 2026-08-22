"""
Project request and response schemas.

Defines Pydantic models for project CRUD operations including
create, get (single), and list (collection) responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Request schema for creating a new project."""

    name: str = Field(min_length=1, max_length=255, description="Project name")
    description: str | None = Field(default=None, max_length=2000, description="Project description")


class ProjectUpdate(BaseModel):
    """Partial update schema for projects.

    All fields are optional — only provided fields are applied.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Project name")
    description: str | None = Field(default=None, max_length=2000, description="Project description")
    status: str | None = Field(default=None, max_length=50, description="Project status")


class ProjectResponse(BaseModel):
    """Response schema for a single project."""

    id: UUID = Field(description="Unique project identifier")
    name: str = Field(description="Project display name")
    description: str | None = Field(default=None, description="Project description")
    status: str = Field(description="Current project status")
    created_by: UUID | None = Field(default=None, description="User who created the project")
    created_at: datetime = Field(description="When the project was created")
    updated_at: datetime = Field(description="When the project was last updated")

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Response schema for a paginated list of projects."""

    items: list[ProjectResponse]
    total: int = Field(ge=0, description="Total number of projects matching the query")
