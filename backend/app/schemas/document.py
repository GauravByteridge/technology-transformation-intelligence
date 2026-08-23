"""
Document request and response schemas.

Defines typed contracts for document search, listing, and management endpoints.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload acceptance (legacy)."""

    message: str = Field(description="Upload status message")
    status: str = Field(description="Processing status of the upload")
    request_id: str = Field(description="Request identifier for traceability")


class DocumentSearchRequest(BaseModel):
    """Request schema for semantic document search."""

    project_id: UUID = Field(description="Project to search within")
    query: str = Field(min_length=1, description="Natural language search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results to return")


class DocumentSearchResponse(BaseModel):
    """Response schema for semantic document search results."""

    results: list[dict] = Field(description="Ranked search results with excerpts and scores")
    total_count: int = Field(description="Number of results returned")
    query: str = Field(description="Original query string")
    project_id: str = Field(description="Project searched")


class DocumentResponse(BaseModel):
    """Response schema for a document record."""

    id: str = Field(description="Document UUID")
    project_id: str = Field(description="Project UUID")
    file_name: str = Field(description="Original file name")
    file_type: str = Field(description="File type extension")
    file_size: int = Field(description="File size in bytes")
    processing_status: str = Field(description="Current processing status")
    created_at: str | None = Field(default=None, description="ISO timestamp of creation")

    model_config = {"from_attributes": True}
