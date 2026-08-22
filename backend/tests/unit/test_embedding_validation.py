"""Tests for embedding dimension startup validation (Task 13.3)."""

import os

import pytest

from app.config.settings import (
    VALID_EMBEDDING_DIMENSIONS,
    Settings,
    validate_live_mode_settings,
)


class TestEmbeddingDimensionValidation:
    """Verify EMBEDDING_DIMENSION validation in Live Mode."""

    def _make_live_settings(
        self, monkeypatch: pytest.MonkeyPatch, embedding_dimension: int = 1536
    ) -> Settings:
        """Create Settings configured for Live Mode with minimal valid config."""
        monkeypatch.setenv("APP_DB_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("RAG_DB_URL", "postgresql+asyncpg://test:test@localhost:5432/rag_db")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "azure_openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
        monkeypatch.setenv("EMBEDDING_DIMENSION", str(embedding_dimension))
        return Settings()

    def test_valid_dimension_1536_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Standard dimension 1536 should pass validation."""
        settings = self._make_live_settings(monkeypatch, embedding_dimension=1536)
        # Should not raise
        validate_live_mode_settings(settings)

    def test_valid_dimension_768_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dimension 768 should pass validation."""
        settings = self._make_live_settings(monkeypatch, embedding_dimension=768)
        validate_live_mode_settings(settings)

    def test_valid_dimension_3072_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Dimension 3072 should pass validation."""
        settings = self._make_live_settings(monkeypatch, embedding_dimension=3072)
        validate_live_mode_settings(settings)

    def test_invalid_dimension_rejects(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-standard dimension should fail validation."""
        settings = self._make_live_settings(monkeypatch, embedding_dimension=999)
        with pytest.raises(ValueError, match="EMBEDDING_DIMENSION mismatch"):
            validate_live_mode_settings(settings)

    def test_zero_dimension_rejects(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Zero dimension should fail validation."""
        settings = self._make_live_settings(monkeypatch, embedding_dimension=0)
        with pytest.raises(ValueError, match="must be a positive integer"):
            validate_live_mode_settings(settings)

    def test_negative_dimension_rejects(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Negative dimension should fail validation."""
        settings = self._make_live_settings(monkeypatch, embedding_dimension=-1)
        with pytest.raises(ValueError, match="must be a positive integer"):
            validate_live_mode_settings(settings)

    def test_all_valid_dimensions_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """All known valid dimensions should pass."""
        for dim in VALID_EMBEDDING_DIMENSIONS:
            settings = self._make_live_settings(monkeypatch, embedding_dimension=dim)
            validate_live_mode_settings(settings)

    def test_demo_mode_skips_dimension_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """In Demo Mode, embedding dimension is not validated."""
        monkeypatch.setenv("APP_DB_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("DEMO_MODE", "true")
        monkeypatch.setenv("EMBEDDING_DIMENSION", "999")
        settings = Settings()
        # Should not raise — Demo Mode skips all Live Mode validation
        validate_live_mode_settings(settings)

    def test_error_message_includes_configured_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Error message should show the invalid configured dimension."""
        settings = self._make_live_settings(monkeypatch, embedding_dimension=2048)
        with pytest.raises(ValueError, match="configured=2048"):
            validate_live_mode_settings(settings)

    def test_error_message_lists_valid_dimensions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Error message should list all valid dimension options."""
        settings = self._make_live_settings(monkeypatch, embedding_dimension=100)
        with pytest.raises(ValueError) as exc_info:
            validate_live_mode_settings(settings)
        error_msg = str(exc_info.value)
        # All valid dimensions should be mentioned
        for dim in VALID_EMBEDDING_DIMENSIONS:
            assert str(dim) in error_msg
