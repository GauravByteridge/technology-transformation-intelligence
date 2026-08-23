"""
Dataset request and response schemas.

Defines typed contracts for dataset and file upload endpoints.
Covers file upload responses, dataset CRUD, preview, query, and region responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response schema for file upload with content-aware processing."""

    file_id: UUID = Field(description="UUID of the created file record")
    file_name: str = Field(description="Original uploaded file name")
    file_type: str = Field(description="Detected file type extension")
    processing_status: str = Field(description="Current processing status")
    datasets_created: list[dict] = Field(
        default_factory=list, description="Datasets created from structured regions"
    )
    documents_indexed: int = Field(
        default=0, description="Number of document chunks indexed for RAG"
    )


class DatasetResponse(BaseModel):
    """Summary response schema for a dataset."""

    id: str = Field(description="Dataset UUID")
    file_id: str = Field(description="Source uploaded file UUID")
    project_id: str | None = Field(default=None, description="Associated project UUID")
    name: str = Field(description="Dataset name")
    source_type: str = Field(description="Source file type (xlsx, csv, json)")
    sheet_name: str | None = Field(default=None, description="Sheet name for multi-sheet files")
    classification: str = Field(description="Content classification (STRUCTURED, SEMI_STRUCTURED)")
    record_count: int = Field(description="Number of records in the dataset")
    confidence: float = Field(description="Classification confidence (0.0 to 1.0)")
    status: str = Field(description="Dataset status (READY, REVIEW_REQUIRED, etc.)")
    created_at: str | None = Field(default=None, description="ISO timestamp of creation")

    model_config = {"from_attributes": True}


class DatasetDetailResponse(DatasetResponse):
    """Detailed response schema extending DatasetResponse with full metadata."""

    description: str | None = Field(default=None, description="Dataset description")
    domain: str | None = Field(default=None, description="Business domain")
    columns: list[dict] = Field(default_factory=list, description="Column schema definitions")
    regions: list[dict] = Field(default_factory=list, description="Associated data regions")


class DatasetPreviewResponse(BaseModel):
    """Response schema for dataset preview with sample rows."""

    dataset: DatasetResponse = Field(description="Dataset summary")
    columns: list[dict] = Field(description="Column schema definitions")
    records: list[dict] = Field(description="Sample data records")
    total_count: int = Field(description="Total record count in the dataset")


class DatasetQueryRequest(BaseModel):
    """Request schema for querying dataset records."""

    filters: dict | None = Field(default=None, description="Column equality filters")
    sort: list[dict] | None = Field(default=None, description="Sort specifications")
    limit: int | None = Field(default=None, description="Maximum records to return")
    offset: int = Field(default=0, description="Number of records to skip")
    columns: list[str] | None = Field(default=None, description="Columns to select")
    aggregations: list[dict] | None = Field(default=None, description="Aggregation operations")


class DatasetQueryResponse(BaseModel):
    """Response schema for dataset query results."""

    records: list[dict] = Field(description="Matching records")
    total_count: int = Field(description="Total matching record count")
    aggregations: list[dict] | None = Field(
        default=None, description="Aggregation results if requested"
    )


class DatasetConfirmRequest(BaseModel):
    """Request schema for confirming or updating a dataset."""

    name: str | None = Field(default=None, description="Updated dataset name")
    description: str | None = Field(default=None, description="Updated description")
    classification: str | None = Field(default=None, description="Updated classification")
    domain: str | None = Field(default=None, description="Updated business domain")


class DataRegionResponse(BaseModel):
    """Response schema for a data region within a file."""

    id: str = Field(description="Region UUID")
    file_id: str = Field(description="Source file UUID")
    dataset_id: str | None = Field(default=None, description="Associated dataset UUID")
    sheet_name: str = Field(description="Sheet name containing this region")
    start_row: int = Field(description="Starting row of the region")
    end_row: int = Field(description="Ending row of the region")
    start_column: int = Field(description="Starting column of the region")
    end_column: int = Field(description="Ending column of the region")
    header_row: int | None = Field(default=None, description="Detected header row index")
    classification: str = Field(description="Content classification")
    processing_strategy: str | None = Field(default=None, description="Assigned processing strategy")
    confidence: float = Field(description="Classification confidence")
    classification_reason: str | None = Field(default=None, description="Explanation of classification")
    warnings: str | None = Field(default=None, description="Validation warnings (JSON)")

    model_config = {"from_attributes": True}
