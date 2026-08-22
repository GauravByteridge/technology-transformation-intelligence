"""Tests for application configuration and startup validation."""

import pytest

from app.config.settings import Settings, validate_live_mode_settings


class TestSettingsLoading:
    """Verify settings load correctly from environment variables."""

    def test_loads_required_variables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_DB_URL", "postgresql+asyncpg://u:p@host:5432/db")
        monkeypatch.setenv("SECRET_KEY", "my-secret")

        settings = Settings()

        assert settings.app_db_url == "postgresql+asyncpg://u:p@host:5432/db"
        assert settings.secret_key == "my-secret"

    def test_demo_mode_defaults_to_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEMO_MODE", raising=False)

        settings = Settings()

        assert settings.demo_mode is True

    def test_optional_defaults(self) -> None:
        settings = Settings()

        assert settings.log_level == "info"
        assert settings.cors_origins == "http://localhost:5173"
        assert settings.app_host == "0.0.0.0"
        assert settings.app_port == 8000

    def test_cors_origin_list_parses_comma_separated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, http://localhost:5173, https://app.example.com")

        settings = Settings()

        assert settings.cors_origin_list == [
            "http://localhost:3000",
            "http://localhost:5173",
            "https://app.example.com",
        ]

    def test_is_live_mode_property(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        settings = Settings()
        assert settings.is_live_mode is True

        monkeypatch.setenv("DEMO_MODE", "true")
        settings = Settings()
        assert settings.is_live_mode is False


class TestDemoModeValidation:
    """Demo Mode must NOT require credentials for unused live providers."""

    def test_demo_mode_does_not_require_llm_credentials(self) -> None:
        settings = Settings()
        assert settings.demo_mode is True

        # Should not raise — no LLM credentials needed
        validate_live_mode_settings(settings)

    def test_demo_mode_passes_even_without_rag_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Demo mode validation passes regardless of RAG/embedding state."""
        monkeypatch.delenv("RAG_DB_URL", raising=False)
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
        monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        settings = Settings(_env_file=None)
        assert settings.demo_mode is True

        # Should not raise — demo mode skips all conditional validation
        validate_live_mode_settings(settings)

    def test_demo_mode_passes_even_without_embedding_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Demo mode validation passes regardless of embedding provider state."""
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

        settings = Settings(_env_file=None)
        assert settings.demo_mode is True

        # Should not raise
        validate_live_mode_settings(settings)


class TestLiveModeValidation:
    """Live Mode validates all required provider/source credentials."""

    def test_live_mode_requires_llm_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        settings = Settings()

        with pytest.raises(ValueError, match="LLM_PROVIDER is required in Live Mode"):
            validate_live_mode_settings(settings)

    def test_live_mode_requires_rag_db_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("RAG_DB_URL", raising=False)

        settings = Settings()

        with pytest.raises(ValueError, match="RAG_DB_URL is required in Live Mode"):
            validate_live_mode_settings(settings)

    def test_live_mode_requires_embedding_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("RAG_DB_URL", "postgresql+asyncpg://u:p@host/rag")
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

        settings = Settings()

        with pytest.raises(ValueError, match="EMBEDDING_PROVIDER is required in Live Mode"):
            validate_live_mode_settings(settings)

    def test_live_mode_azure_foundry_requires_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "azure_foundry")
        monkeypatch.setenv("RAG_DB_URL", "postgresql+asyncpg://u:p@host/rag")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "azure_openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-ada-002")

        settings = Settings()

        with pytest.raises(ValueError) as exc_info:
            validate_live_mode_settings(settings)

        error_msg = str(exc_info.value)
        assert "AZURE_FOUNDRY_API_KEY" in error_msg
        assert "AZURE_FOUNDRY_ENDPOINT" in error_msg
        assert "AZURE_FOUNDRY_MODEL" in error_msg

    def test_live_mode_azure_openai_requires_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "azure_openai")
        monkeypatch.setenv("RAG_DB_URL", "postgresql+asyncpg://u:p@host/rag")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "azure_openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-ada-002")

        settings = Settings()

        with pytest.raises(ValueError) as exc_info:
            validate_live_mode_settings(settings)

        error_msg = str(exc_info.value)
        assert "AZURE_OPENAI_API_KEY" in error_msg
        assert "AZURE_OPENAI_ENDPOINT" in error_msg
        assert "AZURE_OPENAI_DEPLOYMENT" in error_msg

    def test_live_mode_groq_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("RAG_DB_URL", "postgresql+asyncpg://u:p@host/rag")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "azure_openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-ada-002")

        settings = Settings()

        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            validate_live_mode_settings(settings)

    def test_live_mode_passes_with_all_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        monkeypatch.setenv("RAG_DB_URL", "postgresql+asyncpg://u:p@host/rag")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "azure_openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-ada-002")

        settings = Settings()

        # Should not raise
        validate_live_mode_settings(settings)

    def test_live_mode_mongodb_requires_url_when_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        monkeypatch.setenv("RAG_DB_URL", "postgresql+asyncpg://u:p@host/rag")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "azure_openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        monkeypatch.setenv("MONGODB_ENABLED", "true")
        monkeypatch.delenv("MONGODB_URL", raising=False)

        settings = Settings()

        with pytest.raises(ValueError, match="MONGODB_URL is required when MONGODB_ENABLED=true"):
            validate_live_mode_settings(settings)

    def test_mongodb_not_required_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        monkeypatch.setenv("RAG_DB_URL", "postgresql+asyncpg://u:p@host/rag")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "azure_openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        monkeypatch.setenv("MONGODB_ENABLED", "false")

        settings = Settings()

        # Should not raise
        validate_live_mode_settings(settings)
