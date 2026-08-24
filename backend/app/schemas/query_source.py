"""
QuerySourceUsage and Evidence response schemas.

These schemas drive the "Sources Consulted" and "Evidence" panels
in the AI answer UI.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QuerySourceUsageResponse(BaseModel):
    """Response schema for a source consultation record."""

    id: UUID
    query_id: UUID
    data_source_id: UUID
    catalog_entry_id: UUID | None = None
    tool_name: str | None = None
    status: str
    records_retrieved: int = 0
    chunks_retrieved: int = 0
    duration_ms: int | None = None
    error_message: str | None = None
    created_at: datetime

    # Denormalized display fields (populated by service)
    source_name: str | None = None
    source_type: str | None = None
    dataset_name: str | None = None

    model_config = {"from_attributes": True}


class EvidenceResponse(BaseModel):
    """Response schema for a structured evidence item."""

    id: UUID
    query_id: UUID
    query_source_usage_id: UUID
    evidence_type: str
    source_reference: dict | None = None
    content: str | None = None
    structured_value: dict | None = None
    page_number: int | None = None
    sheet_name: str | None = None
    record_reference: str | None = None
    relevance_score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QueryDetailResponse(BaseModel):
    """Full query detail with sources and evidence for Query History."""

    id: UUID
    query_id: UUID
    conversation_id: UUID
    project_id: UUID
    question: str
    response: dict | None = None
    is_partial: bool
    llm_provider: str | None = None
    duration_ms: int | None = None
    sources: list[QuerySourceUsageResponse] = Field(default_factory=list)
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}
