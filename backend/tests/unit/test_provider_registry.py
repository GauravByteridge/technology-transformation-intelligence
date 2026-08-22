"""
Unit tests for the AI provider registry.

Verifies that the registry correctly raises ProviderResolutionError
for unknown provider names, and resolves registered providers.
"""

from collections.abc import AsyncGenerator

import pytest

from app.ai.providers import (
    EmbeddingProvider,
    GenerationResult,
    ProviderRegistry,
    TextGenerationProvider,
)
from app.errors.ai_errors import ProviderResolutionError


# --- Fake providers for testing ---


class FakeTextProvider:
    """Satisfies TextGenerationProvider protocol."""

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> GenerationResult:
        return GenerationResult(text="fake", model="fake-model", usage=None)

    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> AsyncGenerator[str, None]:
        yield "fake"


class FakeEmbeddingProvider:
    """Satisfies EmbeddingProvider protocol."""

    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeDualProvider:
    """Satisfies both TextGenerationProvider and EmbeddingProvider protocols."""

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> GenerationResult:
        return GenerationResult(text="dual", model="dual-model", usage=None)

    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> AsyncGenerator[str, None]:
        yield "dual"

    async def embed(self, text: str) -> list[float]:
        return [0.5, 0.5, 0.5]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.5, 0.5, 0.5] for _ in texts]


# --- Tests ---


class TestProviderRegistryTextProviders:
    """Tests for text generation provider registration and resolution."""

    def test_resolve_unknown_text_provider_raises(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(ProviderResolutionError) as exc_info:
            registry.resolve_text_provider("nonexistent")

        assert exc_info.value.provider_name == "nonexistent"
        assert exc_info.value.supported_providers == []

    def test_resolve_unknown_text_provider_lists_available(self) -> None:
        registry = ProviderRegistry()
        registry.register_text_provider("groq", FakeTextProvider)

        with pytest.raises(ProviderResolutionError) as exc_info:
            registry.resolve_text_provider("unknown")

        assert "unknown" in exc_info.value.provider_name
        assert "groq" in exc_info.value.supported_providers

    def test_resolve_registered_text_provider(self) -> None:
        registry = ProviderRegistry()
        registry.register_text_provider("fake", FakeTextProvider)

        provider = registry.resolve_text_provider("fake")
        assert isinstance(provider, FakeTextProvider)

    def test_list_text_providers_empty(self) -> None:
        registry = ProviderRegistry()
        assert registry.list_text_providers() == []

    def test_list_text_providers_returns_registered_names(self) -> None:
        registry = ProviderRegistry()
        registry.register_text_provider("azure_openai", FakeTextProvider)
        registry.register_text_provider("groq", FakeTextProvider)

        names = registry.list_text_providers()
        assert "azure_openai" in names
        assert "groq" in names


class TestProviderRegistryEmbeddingProviders:
    """Tests for embedding provider registration and resolution."""

    def test_resolve_unknown_embedding_provider_raises(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(ProviderResolutionError) as exc_info:
            registry.resolve_embedding_provider("nonexistent")

        assert exc_info.value.provider_name == "nonexistent"
        assert exc_info.value.supported_providers == []

    def test_resolve_unknown_embedding_provider_lists_available(self) -> None:
        registry = ProviderRegistry()
        registry.register_embedding_provider("azure_openai", FakeEmbeddingProvider)

        with pytest.raises(ProviderResolutionError) as exc_info:
            registry.resolve_embedding_provider("unknown")

        assert "unknown" in exc_info.value.provider_name
        assert "azure_openai" in exc_info.value.supported_providers

    def test_resolve_registered_embedding_provider(self) -> None:
        registry = ProviderRegistry()
        registry.register_embedding_provider("fake", FakeEmbeddingProvider)

        provider = registry.resolve_embedding_provider("fake")
        assert isinstance(provider, FakeEmbeddingProvider)

    def test_list_embedding_providers_empty(self) -> None:
        registry = ProviderRegistry()
        assert registry.list_embedding_providers() == []

    def test_list_embedding_providers_returns_registered_names(self) -> None:
        registry = ProviderRegistry()
        registry.register_embedding_provider("azure_openai", FakeEmbeddingProvider)

        names = registry.list_embedding_providers()
        assert "azure_openai" in names


class TestProviderRegistrySeparation:
    """Tests verifying text and embedding registries are independent."""

    def test_text_and_embedding_registries_are_independent(self) -> None:
        registry = ProviderRegistry()
        registry.register_text_provider("groq", FakeTextProvider)
        registry.register_embedding_provider("azure_openai", FakeEmbeddingProvider)

        # Text registry does not contain embedding providers
        assert "azure_openai" not in registry.list_text_providers()
        # Embedding registry does not contain text providers
        assert "groq" not in registry.list_embedding_providers()

    def test_dual_provider_can_be_registered_in_both(self) -> None:
        registry = ProviderRegistry()
        registry.register_text_provider("dual", FakeDualProvider)
        registry.register_embedding_provider("dual", FakeDualProvider)

        text_provider = registry.resolve_text_provider("dual")
        embedding_provider = registry.resolve_embedding_provider("dual")

        assert isinstance(text_provider, FakeDualProvider)
        assert isinstance(embedding_provider, FakeDualProvider)
