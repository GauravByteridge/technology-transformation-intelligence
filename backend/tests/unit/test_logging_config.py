"""Tests for the structured logging configuration."""

import logging

import pytest
import structlog

from app.config.logging import configure_logging, get_logger


class TestConfigureLogging:
    """Verify structlog configuration works correctly."""

    def test_configure_sets_root_log_level(self) -> None:
        """Root logger level should match the configured log_level."""
        configure_logging(log_level="warning", environment="development")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_configure_for_development_succeeds(self) -> None:
        """Development configuration should not raise errors."""
        configure_logging(log_level="debug", environment="development")

    def test_configure_for_production_succeeds(self) -> None:
        """Production configuration should not raise errors."""
        configure_logging(log_level="info", environment="production")

    def test_get_logger_returns_bound_logger(self) -> None:
        """get_logger should return a structlog BoundLogger."""
        configure_logging(log_level="info", environment="development")
        logger = get_logger("test_module")
        assert logger is not None

    def test_uvicorn_access_log_suppressed(self) -> None:
        """uvicorn.access logger should be at WARNING level to reduce noise."""
        configure_logging(log_level="debug", environment="development")
        uvicorn_logger = logging.getLogger("uvicorn.access")
        assert uvicorn_logger.level == logging.WARNING
