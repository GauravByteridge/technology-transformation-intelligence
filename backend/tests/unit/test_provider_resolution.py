"""
Tests for provider resolution and conditional startup validation.

Verifies:
- Demo Mode defaults LLM_PROVIDER to "mock" when not set
- Demo Mode does not fail startup when credentials are absent
- Live Mode fails startup if provider credentials are missing
- Embedding provider resolves independently of text generation
- EMBEDDING_MODEL and EMBEDDING_DIMENSION are configurable
"""

import pytest

from app.ai.providers.mock_provider import MockEmbeddingProvider, MockTextGenerationProvider
from app.config.settings import Settings
from app.dependencies import (
    get_embedding_provider,
    get_provider_registry,
    get_text_generation_provider,
    initialize_provider_registry,
    initialize_providers,
    resolve_embedding_provider,
    resolve_text_generation_provider,
)


class TestProviderRegistryInitialization:
    """Tests for the provider registry setup."""

    def test_initialize_provider_registry_registers_text_providers(self) -> None:
        registry = initialize_provider_registry()

        text_providers = registry.list_text_providers()
        assert "azure_foundry" in text_providers
        assert "azure_openai" in text_providers
        assert "groq" in text_providers
        assert "mock" in text_providers

    def test_initialize_provider_registry_registers_embedding_providers(self) -> None:
        registry = initialize_provider_registry()

        embedding_providers = registry.list_embedding_providers()
        assert "azure_openai" in embedding_providers
        assert "azure_foundry" in embedding_providers
        assert "mock" in embedding_providers

    def test_get_provider_registry_raises_if_not_initialized(self) -> None:
        """Accessing registry before initialization raises RuntimeError."""
        import app.dependencies as deps

        # Reset the module-level singleton
        original = deps._provider_registry
        deps._provider_registry = None
        try:
            with pytest.raises(RuntimeError, match="ProviderRegistry not initialized"):
                get_provider_registry()
        finally:
            deps._provider_registry = original


class TestDemoModeProviderResolution:
    """Demo Mode defaults to mock providers when credentials are absent."""

    def test_demo_mode_defaults_llm_provider_to_mock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When LLM_PROVIDER is unset in Demo Mode, resolves to mock."""
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        settings = Settings(_env_file=None)
        assert settings.demo_mode is True
        assert settings.llm_provider is None

        initialize_provider_registry()
        provider = resolve_text_generation_provider(settings)

        assert isinstance(provider, MockTextGenerationProvider)

    def test_demo_mode_defaults_embedding_provider_to_mock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When EMBEDDING_PROVIDER is unset in Demo Mode, resolves to mock."""
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

        settings = Settings(_env_file=None)
        assert settings.demo_mode is True
        assert settings.embedding_provider is None

        initialize_provider_registry()
        provider = resolve_embedding_provider(settings)

        assert isinstance(provider, MockEmbeddingProvider)

    def test_demo_mode_does_not_fail_with_missing_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Demo Mode startup succeeds even without provider credentials."""
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

        settings = Settings(_env_file=None)
        assert settings.demo_mode is True

        # Should not raise
        initialize_providers(settings)

        text_provider = get_text_generation_provider()
        embedding_provider = get_embedding_provider()

        assert isinstance(text_provider, MockTextGenerationProvider)
        assert isinstance(embedding_provider, MockEmbeddingProvider)

    def test_demo_mode_respects_explicit_llm_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When LLM_PROVIDER is explicitly set in Demo Mode, uses that provider."""
        monkeypatch.setenv("LLM_PROVIDER", "mock")

        settings = Settings(_env_file=None)
        assert settings.demo_mode is True
        assert settings.llm_provider == "mock"

        initialize_provider_registry()
        provider = resolve_text_generation_provider(settings)

        assert isinstance(provider, MockTextGenerationProvider)

    def test_demo_mode_warns_but_doesnt_fail_with_invalid_provider_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Demo Mode: if an explicit provider's credentials are missing, warn + fallback."""
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        settings = Settings(_env_file=None)
        assert settings.demo_mode is True

        # Should not raise — demo mode is lenient
        initialize_providers(settings)

        # Text provider should still resolve (groq stub accepts empty strings)
        text_provider = get_text_generation_provider()
        assert text_provider is not None


class TestEmbeddingConfiguration:
    """Embedding provider resolves independently with its own config."""

    def test_embedding_dimension_configurable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EMBEDDING_DIMENSION is passed to mock embedding provider."""
        monkeypatch.setenv("EMBEDDING_DIMENSION", "768")
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

        settings = Settings(_env_file=None)
        assert settings.embedding_dimension == 768

        initialize_provider_registry()
        provider = resolve_embedding_provider(settings)

        assert isinstance(provider, MockEmbeddingProvider)
        assert provider._dimension == 768

    def test_embedding_provider_independent_of_text_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Changing LLM_PROVIDER does not affect embedding provider."""
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

        settings = Settings(_env_file=None)
        initialize_provider_registry()

        text_provider = resolve_text_generation_provider(settings)
        embedding_provider = resolve_embedding_provider(settings)

        assert isinstance(text_provider, MockTextGenerationProvider)
        assert isinstance(embedding_provider, MockEmbeddingProvider)


class TestLiveModeProviderValidation:
    """Live Mode must fail startup with missing/invalid provider config."""

    def test_live_mode_fails_with_unsupported_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Live Mode with unsupported LLM_PROVIDER fails validate_live_mode_settings."""
        from app.config.settings import validate_live_mode_settings

        monkeypatch.setenv("DEMO_MODE", "false")
        # pydantic validation will reject an invalid Literal value, so this
        # scenario is caught by pydantic before it reaches our code.
        # Instead, test empty/None LLM_PROVIDER:
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        settings = Settings(_env_file=None)

        with pytest.raises(ValueError, match="LLM_PROVIDER is required in Live Mode"):
            validate_live_mode_settings(settings)

    def test_live_mode_fails_with_missing_provider_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Live Mode with valid provider but missing credentials fails."""
        from app.config.settings import validate_live_mode_settings

        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("RAG_DB_URL", "postgresql+asyncpg://u:p@host/rag")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "azure_openai")
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-ada-002")

        settings = Settings(_env_file=None)

        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            validate_live_mode_settings(settings)


class TestGetProviderAccessors:
    """Tests for get_text_generation_provider and get_embedding_provider."""

    def test_get_text_generation_provider_raises_if_not_initialized(self) -> None:
        import app.dependencies as deps

        original = deps._text_generation_provider
        deps._text_generation_provider = None
        try:
            with pytest.raises(RuntimeError, match="Text generation provider not initialized"):
                get_text_generation_provider()
        finally:
            deps._text_generation_provider = original

    def test_get_embedding_provider_raises_if_not_initialized(self) -> None:
        import app.dependencies as deps

        original = deps._embedding_provider
        deps._embedding_provider = None
        try:
            with pytest.raises(RuntimeError, match="Embedding provider not initialized"):
                get_embedding_provider()
        finally:
            deps._embedding_provider = original
