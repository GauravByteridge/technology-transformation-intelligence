"""
Configuration response schemas.

Defines typed contracts for configuration-related API endpoints.
"""

from pydantic import BaseModel, Field


class AppModeResponse(BaseModel):
    """Response schema exposing the current application mode."""

    mode: str = Field(description="Current operating mode: 'demo' or 'live'")
    demo_mode: bool = Field(description="True if running in Demo Mode")
    request_id: str = Field(description="Request identifier for traceability")
