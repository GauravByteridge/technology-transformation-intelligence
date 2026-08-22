"""
Document request and response schemas.

Defines typed contracts for document upload and management endpoints.
"""

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload acceptance."""

    message: str = Field(description="Upload status message")
    status: str = Field(description="Processing status of the upload")
    request_id: str = Field(description="Request identifier for traceability")
