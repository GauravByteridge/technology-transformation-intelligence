"""Pydantic request/response models for the Project Intelligence Hub API."""

from datetime import datetime
from enum import Enum
from typing import Optional, Literal

from pydantic import BaseModel


class FileCategory(str, Enum):
    """Categories for uploaded files."""

    PROJECT_COSTS = "Project Costs"
    BURNDOWN = "Burndown"
    AUDIT = "Audit"
    IT_CONTROLS = "IT Controls"
    REMEDIATION = "Remediation"
    BUSINESS_INTELLIGENCE = "Business Intelligence"
    INTERNAL_DATA = "Internal Data"
    OTHER = "Other"


class ProjectCreate(BaseModel):
    """Request model for creating a new project."""

    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    """Response model for project data."""

    id: int
    name: str
    description: Optional[str]
    created_at: datetime


class FileResponse(BaseModel):
    """Response model for file metadata."""

    id: int
    file_name: str
    file_type: str
    category: FileCategory
    uploaded_at: datetime
    chunk_count: int


class ChatRequest(BaseModel):
    """Request model for chat queries."""

    question: str


class ChatResponse(BaseModel):
    """Response model for chat answers."""

    answer: str
    sources: list[str]


class VisualizationRequest(BaseModel):
    """Request model for visualization generation."""

    query: str


class ChartConfig(BaseModel):
    """Response model for chart configuration."""

    type: Literal["bar", "line", "pie"]
    title: str
    data: list[dict]
    x_key: Optional[str] = None
    y_key: Optional[str] = None
    data_key: Optional[str] = None
    name_key: Optional[str] = None


class DashboardStats(BaseModel):
    """Response model for dashboard statistics."""

    project_name: str
    project_description: Optional[str]
    total_files: int
    files_by_type: list[dict]
    files_by_category: list[dict]
    recent_files: list[FileResponse]


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str
