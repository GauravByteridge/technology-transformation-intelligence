"""
Unit tests for the MockTextGenerationProvider.

Verifies deterministic responses, correct model metadata,
and streaming behavior without external API calls.
"""

import pytest

from app.ai.providers.mock_provider import (
    MOCK_MODEL,
    MOCK_RESPONSE,
    MockTextGenerationProvider,
)
from app.ai.providers.protocol import GenerationResult


class TestMockTextGenerationProviderGenerate:
    """Tests for the generate method."""

    @pytest.mark.asyncio
    async def test_generate_returns_generation_result(self) -> None:
        provider = MockTextGenerationProvider()
        result = await provider.generate("What is project health?")

        assert isinstance(result, GenerationResult)

    @pytest.mark.asyncio
    async def test_generate_returns_deterministic_text(self) -> None:
        provider = MockTextGenerationProvider()
        result_1 = await provider.generate("First prompt")
        result_2 = await provider.generate("Different prompt")

        assert result_1.text == result_2.text
        assert result_1.text == MOCK_RESPONSE

    @pytest.mark.asyncio
    async def test_generate_uses_mock_model_name(self) -> None:
        provider = MockTextGenerationProvider()
        result = await provider.generate("test")

        assert result.model == MOCK_MODEL

    @pytest.mark.asyncio
    async def test_generate_includes_usage_metadata(self) -> None:
        provider = MockTextGenerationProvider()
        result = await provider.generate("test")

        assert result.usage is not None
        assert "prompt_tokens" in result.usage
        assert "completion_tokens" in result.usage
        assert "total_tokens" in result.usage

    @pytest.mark.asyncio
    async def test_generate_ignores_system_prompt(self) -> None:
        provider = MockTextGenerationProvider()
        result = await provider.generate("test", system_prompt="You are an analyst.")

        assert result.text == MOCK_RESPONSE

    @pytest.mark.asyncio
    async def test_generate_ignores_kwargs(self) -> None:
        provider = MockTextGenerationProvider()
        result = await provider.generate("test", temperature=0.7, max_tokens=100)

        assert result.text == MOCK_RESPONSE


class TestMockTextGenerationProviderStream:
    """Tests for the stream method."""

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self) -> None:
        provider = MockTextGenerationProvider()
        chunks: list[str] = []

        async for chunk in provider.stream("test"):
            chunks.append(chunk)

        assert len(chunks) > 1

    @pytest.mark.asyncio
    async def test_stream_reconstructs_to_full_response(self) -> None:
        provider = MockTextGenerationProvider()
        chunks: list[str] = []

        async for chunk in provider.stream("test"):
            chunks.append(chunk)

        reassembled = "".join(chunks)
        assert reassembled == MOCK_RESPONSE

    @pytest.mark.asyncio
    async def test_stream_is_deterministic(self) -> None:
        provider = MockTextGenerationProvider()

        chunks_1: list[str] = []
        async for chunk in provider.stream("prompt A"):
            chunks_1.append(chunk)

        chunks_2: list[str] = []
        async for chunk in provider.stream("prompt B"):
            chunks_2.append(chunk)

        assert chunks_1 == chunks_2


class TestMockProviderRegistration:
    """Tests verifying mock provider works with the registry."""

    def test_mock_provider_registers_and_resolves(self) -> None:
        from app.ai.providers import ProviderRegistry

        registry = ProviderRegistry()
        registry.register_text_provider("mock", MockTextGenerationProvider)

        provider = registry.resolve_text_provider("mock")
        assert isinstance(provider, MockTextGenerationProvider)
