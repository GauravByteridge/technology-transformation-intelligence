"""
Common schema re-exports.

Barrel module that provides convenient access to shared schemas
(ErrorResponse, FieldError, HealthResponse) from a single import path.
"""

from app.schemas.error import ErrorResponse, FieldError
from app.schemas.health import HealthResponse

__all__ = [
    "ErrorResponse",
    "FieldError",
    "HealthResponse",
]
