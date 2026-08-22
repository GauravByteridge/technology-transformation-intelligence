"""
Data source request and response schemas.

Defines typed contracts for data source API endpoints,
including connection testing and configuration.
"""

from pydantic import BaseModel, Field


class TestConnectionResponse(BaseModel):
    """Response schema for data source connection test."""

    success: bool = Field(description="Whether the connection test succeeded")
    source_type: str = Field(description="Type of the data source tested")
    source_name: str = Field(description="Name of the data source tested")
    message: str = Field(description="Human-readable result message")
    request_id: str = Field(description="Request identifier for traceability")
