"""
Error response schemas.

Defines the consistent error response body returned by all API endpoints
when an error occurs. Matches the contract specified in Requirement 13.3.
"""

from pydantic import BaseModel, Field


class FieldError(BaseModel):
    """Describes a single field validation error."""

    field: str = Field(description="Name of the field that failed validation")
    message: str = Field(description="Description of the validation failure")


class ErrorResponse(BaseModel):
    """
    Consistent error response schema for all API errors.

    Returned for all 4xx and 5xx responses to provide structured,
    machine-readable error information with traceability.
    """

    error_code: str = Field(description="Machine-readable error identifier")
    message: str = Field(description="Human-readable error description")
    request_id: str = Field(description="Unique request identifier for traceability")
    detail: str | None = Field(default=None, description="Additional context (omitted in 500 responses)")
    field_errors: list[FieldError] | None = Field(
        default=None,
        description="Field-level validation errors (present only for 422 responses)",
    )
