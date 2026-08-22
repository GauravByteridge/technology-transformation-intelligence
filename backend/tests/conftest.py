"""Shared test fixtures for the backend test suite."""

import os

import pytest


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide minimal required environment variables for all tests."""
    monkeypatch.setenv("APP_DB_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing")
    monkeypatch.setenv("DEMO_MODE", "true")
