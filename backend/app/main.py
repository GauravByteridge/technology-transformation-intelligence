"""
FastAPI application entry point.

Configures the application with:
- Lifespan handler for startup/shutdown validation
- CORS middleware based on environment configuration
- Request ID middleware for traceability (UUID v4 stored in ContextVar)
- Structured logging via structlog with request_id correlation
- Global exception handlers for consistent error responses
- API router mounted at /api/v1/
"""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config.logging import configure_logging, get_logger
from app.config.settings import validate_live_mode_settings
from app.dependencies import (
    get_settings,
    initialize_ai_service,
    initialize_app_db,
    initialize_connector_registry,
    initialize_providers,
    initialize_tool_registry,
)
from app.errors import register_exception_handlers
from app.middleware.request_id import request_id_ctx

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler — runs startup validation and teardown.

    Startup:
    - Configures structured logging
    - Loads and validates settings
    - In Live Mode, validates all conditional provider/source credentials
    - Fails fast with descriptive error if configuration is invalid

    Shutdown:
    - Placeholder for resource cleanup (DB pools, HTTP clients)
    """
    settings = get_settings()

    # Configure structured logging early so all startup messages are structured
    environment = "production" if settings.is_live_mode else "development"
    configure_logging(log_level=settings.log_level, environment=environment)

    # Validate conditional configuration based on mode
    try:
        validate_live_mode_settings(settings)
    except ValueError as exc:
        logger.error("startup_validation_failed", error=str(exc))
        raise SystemExit(1) from exc

    # Initialize App_DB session factory for repository layer
    initialize_app_db(settings)

    # Initialize ConnectorRegistry with all built-in connectors
    initialize_connector_registry()

    # Initialize AI provider registry and resolve configured providers
    initialize_providers(settings)

    # Initialize AI tool registry and AI service
    initialize_tool_registry()
    initialize_ai_service(settings)

    mode = "Demo" if settings.demo_mode else "Live"
    logger.info(
        "application_starting",
        mode=mode,
        host=settings.app_host,
        port=settings.app_port,
    )

    yield

    # Shutdown — cleanup resources
    logger.info("application_shutting_down")


def create_app() -> FastAPI:
    """
    Application factory — builds and configures the FastAPI instance.

    Separated from module-level instantiation to support testing
    with different configurations.
    """
    settings = get_settings()

    app = FastAPI(
        title="Technology Transformation Intelligence Platform",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS — origins loaded from CORS_ORIGINS environment variable
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register global exception handlers (before middleware registration)
    register_exception_handlers(app)

    # Request ID middleware — generates UUID v4, stores in ContextVar, adds to response header
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:  # noqa: ANN001
        """Attach a unique request_id to each request for traceability."""
        generated_id = str(uuid.uuid4())
        # Store in ContextVar for structured logging access across the request lifecycle
        request_id_ctx.set(generated_id)
        # Also store on request state for direct access in route handlers
        request.state.request_id = generated_id
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            # NOTE: Unhandled exceptions that escape through BaseHTTPMiddleware
            # are caught here. Full details logged server-side only.
            from app.errors.handlers import unhandled_exception_handler

            return await unhandled_exception_handler(request, exc)
        response.headers["X-Request-ID"] = generated_id
        return response

    # Mount versioned API router
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
