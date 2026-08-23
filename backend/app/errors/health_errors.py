"""
Health and finance domain error types.

Raised by health and finance services when domain-specific
operations fail.
"""

from app.errors.base import AppError, ErrorCategory


class HealthKpiNotFoundError(AppError):
    """Raised when health KPI data does not exist for a project."""

    def __init__(self, project_id: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="HEALTH_KPI_NOT_FOUND",
            message=f"Health KPI data not found for project '{project_id}'",
            domain="health",
            category=ErrorCategory.NOT_FOUND,
            detail=detail,
        )


class FinanceDataNotFoundError(AppError):
    """Raised when no budget exists for a project."""

    def __init__(self, project_id: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="FINANCE_DATA_NOT_FOUND",
            message=f"Finance data not found for project '{project_id}'",
            domain="finance",
            category=ErrorCategory.NOT_FOUND,
            detail=detail,
        )
