"""
Project domain error types.

Raised by project services and repositories when project-related
operations fail.
"""

from app.errors.base import AppError, ErrorCategory


class ProjectNotFoundError(AppError):
    """Raised when a requested project does not exist."""

    def __init__(self, project_id: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="PROJECT_NOT_FOUND",
            message=f"Project '{project_id}' not found",
            domain="project",
            category=ErrorCategory.NOT_FOUND,
            detail=detail,
        )


class ProjectValidationError(AppError):
    """Raised when project input fails validation rules."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="PROJECT_VALIDATION_ERROR",
            message=message,
            domain="project",
            category=ErrorCategory.VALIDATION,
            detail=detail,
        )
