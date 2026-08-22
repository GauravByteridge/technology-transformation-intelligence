"""
Pydantic request/response schemas.

Re-exports key models for convenient imports:
    from app.schemas import ErrorResponse, ProjectCreate, AIResponse, ...
"""

from app.schemas.ai import AIQueryRequest, AIResponse
from app.schemas.error import ErrorResponse, FieldError
from app.schemas.health import HealthResponse
from app.schemas.projects import ProjectCreate, ProjectListResponse, ProjectResponse

__all__ = [
    # Error schemas
    "ErrorResponse",
    "FieldError",
    # Health
    "HealthResponse",
    # Projects
    "ProjectCreate",
    "ProjectResponse",
    "ProjectListResponse",
    # AI
    "AIQueryRequest",
    "AIResponse",
]
