"""
Lineage request/response schemas.

Defines Pydantic models for lineage graph data used in the
Data Lineage UI panel.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LineageNodeResponse(BaseModel):
    """Response schema for a single lineage graph node."""

    id: UUID
    node_type: str
    node_key: str
    label: str
    source_id: UUID | None = None
    catalog_entry_id: UUID | None = None
    tool_name: str | None = None
    metadata: dict | None = None
    sequence_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LineageRunResponse(BaseModel):
    """Response schema for a full lineage graph."""

    id: UUID
    query_id: UUID
    nodes: list[LineageNodeResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}
