"""
Backward-compatible re-export.

The canonical location for project schemas is app.schemas.projects.
This module exists to maintain imports in existing code.
"""

from app.schemas.projects import ProjectCreate, ProjectListResponse, ProjectResponse

__all__ = [
    "ProjectCreate",
    "ProjectListResponse",
    "ProjectResponse",
]
