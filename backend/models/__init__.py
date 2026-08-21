# Models Module
# Contains Pydantic models and SQLAlchemy ORM models

from models.schemas import (
    FileCategory,
    ProjectCreate,
    ProjectResponse,
    FileResponse,
    ChatRequest,
    ChatResponse,
    VisualizationRequest,
    ChartConfig,
    DashboardStats,
    ErrorResponse,
)

__all__ = [
    "FileCategory",
    "ProjectCreate",
    "ProjectResponse",
    "FileResponse",
    "ChatRequest",
    "ChatResponse",
    "VisualizationRequest",
    "ChartConfig",
    "DashboardStats",
    "ErrorResponse",
]

try:
    from models.database_models import File, Project

    __all__ += ["Project", "File"]
except Exception:
    # Database models may not be available if DB dependencies aren't installed
    pass
