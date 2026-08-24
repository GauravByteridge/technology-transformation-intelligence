"""
Structured logging configuration using structlog.

Configures structlog with:
- JSON rendering for production (machine-parseable)
- Console rendering for development (human-readable)
- Automatic inclusion of request_id, timestamp, and log level in every entry
- Integration with Python's standard logging for third-party library output
- Credential filtering to prevent accidental secret exposure

The request_id is bound from the ContextVar set by RequestIdMiddleware,
ensuring all log entries within a request share the same correlation ID.
"""

import logging
import re
import sys
from typing import Literal

import structlog

from app.middleware.request_id import request_id_ctx


# WARNING: Patterns that identify credential-like values in log output.
# Any match is redacted before the log entry is emitted.
_LOG_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(connection[_-]?string|conn[_-]?str)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(token|bearer)\s*[:=]\s*\S+"),
    re.compile(r"postgresql(\+\w+)?://\S+:\S+@"),
    re.compile(r"mongodb(\+srv)?://\S+:\S+@"),
]

_REDACTED = "[REDACTED]"


def _add_request_id(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Inject the current request_id from ContextVar into every log entry."""
    current_request_id = request_id_ctx.get("")
    if current_request_id:
        event_dict["request_id"] = current_request_id
    return event_dict


def _filter_credentials(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Redact credential-like patterns from all string values in the log entry.

    Scans both the event message and all extra fields to prevent accidental
    exposure of database URLs, API keys, passwords, or tokens.
    """
    for key, value in event_dict.items():
        if isinstance(value, str):
            for pattern in _LOG_SENSITIVE_PATTERNS:
                if pattern.search(value):
                    event_dict[key] = pattern.sub(_REDACTED, value)
                    value = event_dict[key]
    return event_dict


def configure_logging(
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info",
    environment: str = "development",
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Minimum log level to emit.
        environment: When "production", uses JSON rendering; otherwise console.
    """
    is_production = environment.lower() == "production"
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Shared processors applied to every log entry
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        _filter_credentials,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        # JSON output for production log aggregation
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Human-readable colored console output for development
        renderer = structlog.dev.ConsoleRenderer()

    # On Windows, stdout may default to cp1252 which cannot encode Unicode
    # characters used by ConsoleRenderer. Force UTF-8 output in that case.
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    structlog.configure(
        processors=[
            *shared_processors,
            renderer,
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to route through structlog
    # This captures output from uvicorn, sqlalchemy, and other libraries
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *shared_processors,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structlog logger instance.

    Args:
        name: Optional logger name (typically __name__ of the calling module).

    Returns:
        A bound structlog logger with request_id automatically injected.
    """
    return structlog.get_logger(name)
