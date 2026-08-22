"""
Global exception handlers for the FastAPI application.

Catches domain errors (AppError subclasses), validation errors,
and unhandled exceptions — returning consistent ErrorResponse bodies.

500 responses never expose stack traces, file paths, or class names.
"""

import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors.base import AppError
from app.schemas.error import ErrorResponse, FieldError

logger = structlog.get_logger(__name__)


def _get_request_id(request: Request) -> str:
    """Extract request_id from request state, or generate a fallback."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Handle domain errors (AppError subclasses).

    Maps the error category to an HTTP status code and returns
    a structured ErrorResponse.
    """
    request_id = _get_request_id(request)
    status_code = exc.http_status_code

    logger.warning(
        "Domain error",
        error_code=exc.error_code,
        message=exc.message,
        domain=exc.domain,
        category=exc.category,
        status_code=status_code,
        request_id=request_id,
        path=request.url.path,
    )

    response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        request_id=request_id,
        detail=exc.detail,
        field_errors=None,
    )

    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(exclude_none=True),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic/FastAPI request validation errors.

    Returns 422 with field-level error details.
    """
    request_id = _get_request_id(request)

    field_errors = [
        FieldError(
            field=" → ".join(str(loc) for loc in err.get("loc", [])),
            message=err.get("msg", "Validation failed"),
        )
        for err in exc.errors()
    ]

    logger.info(
        "Request validation failed",
        request_id=request_id,
        path=request.url.path,
        error_count=len(field_errors),
    )

    response = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        request_id=request_id,
        detail=None,
        field_errors=field_errors,
    )

    return JSONResponse(
        status_code=422,
        content=response.model_dump(exclude_none=True),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle Starlette/FastAPI HTTP exceptions (e.g., 404 from path not found).

    Wraps them in the consistent ErrorResponse schema.
    """
    request_id = _get_request_id(request)

    logger.info(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        request_id=request_id,
        path=request.url.path,
    )

    response = ErrorResponse(
        error_code="HTTP_ERROR",
        message=str(exc.detail) if exc.detail else "An error occurred",
        request_id=request_id,
        detail=None,
        field_errors=None,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(exclude_none=True),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unhandled exceptions.

    Returns a generic 500 response without exposing any internal details
    (no stack traces, file paths, or class names).
    Logs the full error server-side for debugging.
    """
    request_id = _get_request_id(request)

    # NOTE: Full exception logged server-side only — never exposed to client
    logger.error(
        "Unhandled exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
        exc_message=str(exc),
        exc_info=True,
    )

    response = ErrorResponse(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        request_id=request_id,
        detail=None,
        field_errors=None,
    )

    return JSONResponse(
        status_code=500,
        content=response.model_dump(exclude_none=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application.

    Called during app creation in main.py.
    """
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]
