"""
File metadata request/response schemas.

Defines Pydantic models for uploaded file metadata CRUD operations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FileCreate(BaseModel):
    """Request schema for creating a file metadata record."""

    project_id: UUID = Field(description="Project this file belongs to")
    data_source_id: UUID | None = Field(default=None, description="Optional data source association")
    file_name: str = Field(min_length=1, max_length=500, description="Original file name")
    file_type: str = Field(min_length=1, max_length=50, description="File MIME type or extension")
    file_size: int = Field(gt=0, description="File size in bytes")


class FileUpdate(BaseModel):
    """Partial update schema for file records (primarily processing status)."""

    processing_status: str | None = Field(default=None, max_length=50, description="Processing status")
    processing_error: str | None = Field(default=None, description="Processing error message if failed")


class FileResponse(BaseModel):
    """Response schema for a file metadata record."""

    id: UUID
    project_id: UUID
    data_source_id: UUID | None = None
    file_name: str
    file_type: str
    file_size: int
    processing_status: str
    processing_error: str | None = None
    uploaded_by: UUID
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
